#include <iostream>
#include <unistd.h>
#include <math.h>

// many thanks to:
// https://stackoverflow.com/questions/53688777/how-to-implement-x11return-colour-of-a-screen-pixel-c-code-for-luajits-ffi
// https://kukuruku.co/post/a-cheat-sheet-for-http-libraries-in-c/
// https://stackoverflow.com/questions/9786150/save-curl-content-result-into-a-string-in-c
// https://stackoverflow.com/questions/19555121/how-to-get-current-timestamp-in-milliseconds-since-1970-just-the-way-java-gets
// https://stackoverflow.com/questions/7868936/read-file-line-by-line-using-ifstream-in-c#7868998
// https://stackoverflow.com/questions/216823/whats-the-best-way-to-trim-stdstring

#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <curl/curl.h>
#include <sys/time.h>
#include <fstream>
#include <sstream>
#include <boost/algorithm/string.hpp>

// color modes
#define SCREEN_COLOR "continuous"
#define STATIC "static"

// error codes
#define OK = 200
#define ERROR 500
#define CONFLICT 409

// for how long was no answer received from the server?
float timeout = 0;

// bad practice apparently:
using namespace std;


long get_us()
{
    /* this function returns the microseconds since 1970 */
    struct timeval time;
    gettimeofday(&time, NULL);
    long us = time.tv_sec * 1000000 + time.tv_usec;
    return us;
}


void sendcolor(int r, int g, int b, char * ip, int port, int checks_per_second,
        int client_id, string mode, int max_timeout, long * last_message_timestamp,
        int verbose_level)
{
    /* seoncds a get request to the LED server using curl
     * - r, g and b are the colors between 0 and full_on
     * - ip and port those of the raspberry
     * - check_per_second is how often this client will (try to) make such reqeusts per seoncds
     * - client_id is an identifier for the current "stream" of messages from this client
     * - mode should be SCREEN_COLOR
     * - max_timeout is read from the config file. it's an integer of seconds. The code will stop when
     * no communication is received within that amount of time.
     * - last_message_timestamp is a pointer to a get_us() value of the last successful communciation */

    CURL *curl;

    int handle_count;

    curl = curl_easy_init();
    if(curl)
    {
        char url[100];
        sprintf(url, "%s:%d/color/set/?r=%d&g=%d&b=%d&cps=%d&id=%d&mode=%s", 
                ip, port, r, g, b, checks_per_second, client_id, mode.c_str());

        if(verbose_level >= 1) cout << "sending GET pramas: " << url << "\n";

        curl_easy_setopt(curl, CURLOPT_URL, url);
        // 1 second timeout for curl, which might add up
        // to max_timeout for multiple lost messages.
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 1);
        CURLcode status = curl_easy_perform(curl);
        long http_code = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);

        curl_easy_cleanup(curl);

        if(http_code == CONFLICT)
        {
            cout << "server closed connection with this client to prevent duplicate "
                    "connections. Another client started sending to the server!" << endl;
            exit(1);
        }

        // check if server is available if for 5 seconds no color reached it
        if(status != CURLE_OK)
        {
            // how much time passed since the last successful communication?
            float timeout = (float)(get_us() - *last_message_timestamp) / 1000000;

            if(timeout >= max_timeout)
            {
                cout << "timeout! cannot reach server!" << endl;
                exit(1);
            }
            else
            {
                cout << "server did not send a response for " << timeout << "s" << endl;
            }
        }
        else
        {
            *last_message_timestamp = get_us();
        }
    }
}


void parse_float_array(string strvalue, int size, float *array)
{
    /* given a string like 1.10,0.88,0.7
     * overwrites the values in the array parameter to
     * {1.10, 0.88, 0.7}
     * in this case the size param would be 3 */

    // more complicated stuff, one float per channel in array
    int channel = 0;
    int j = 0;
    // remember last comma position
    int start = 0;
    while(true)
    {
        if(strvalue[j] == ',' or strvalue[j] == '\0')
        {
            float value = atof(strvalue.substr(start, j).c_str());
            array[channel] = value;
            channel ++;
            start = j+1;
        }
        if(strvalue[j] == '\0') break;
        j++;
    }
}


int main(int argc, char * argv[])
{
    // default params:

    // screen
    int screen_width = 1920;
    int screen_height = 1080;

    // sampling
    int smoothing = 3;
    int checks_per_second = 2;
    int columns = 50;
    int lines = 3;

    // hardware
    string raspberry_ip = "";
    int raspberry_port = 3546;

    int max_timeout = 10;

    // colors
    // if true, will use a window average for smoothing
    // if false, weights the old color by smoothing and averages,
    // creating an "ease out" effect but produces artifacts when fading to black
    // because incremential changes will start to produce jumping hues.
    bool linear_smoothing = true;
    float brightness[3] = {1.00, 0.85, 0.5};
    float gamma[3] = {1.10, 0.88, 0.7};
    // 0 = no nrmalization, 0.5 = increase lightness, 1 = normalize to full_on
    float normalize = 0;
    // if false, will normalize the max value to full_on, if true wil normalize the sum to it
    // setting it to true will basically favor saturated colors over grey/white ones during normalization
    bool normalize_sum = true;
    // 0 = no adjustment, 0.5 = increases saturation, 1 = darkest color becomes 0 (prevents gray values alltogether)
    float increase_saturation = 0.5;

    // some debugging stuff
    int verbose_level = 1;

    // overwrite default params with params from config file
    ifstream infile(argv[1]);
    string line;
    bool config_exists = false;
    while (getline(infile, line))
    {
        config_exists = true;
        boost::trim(line);

        // skip comments
        if(line[0] == '#')
            continue;

        // search for equal symbol
        for(int i = 0; line[i] != '\0'; i++)
        {
            if(line[i] == '=')
            {
                string key = line.substr(0, i);
                string strvalue = line.substr(i+1);
                // trim in-place
                boost::trim(key);
                boost::trim(strvalue);

                // depending on the key, parse the value in different ways
                try
                {
                    // yes i do find this more convenient than switch case break
                    if(key == "raspberry_port") raspberry_port = stoi(strvalue);
                    else if(key == "raspberry_ip") raspberry_ip = strvalue;
                    else if(key == "screen_width") screen_width = stoi(strvalue);
                    else if(key == "screen_height") screen_height = stoi(strvalue);
                    else if(key == "increase_saturation") increase_saturation = atof(strvalue.c_str());
                    else if(key == "normalize") normalize = atof(strvalue.c_str());
                    else if(key == "lines") lines = stoi(strvalue);
                    else if(key == "columns") columns = stoi(strvalue);
                    else if(key == "smoothing") smoothing = stoi(strvalue);
                    else if(key == "checks_per_second") checks_per_second = stoi(strvalue);
                    else if(key == "brightness") parse_float_array(strvalue, 3, brightness);
                    else if(key == "gamma") parse_float_array(strvalue, 3, gamma);
                    else if(key == "linear_smoothing") linear_smoothing = stoi(strvalue);
                    else if(key == "max_timeout") max_timeout = stoi(strvalue);
                    else if(key == "verbose_level") verbose_level = stoi(strvalue);
                }
                catch (invalid_argument e)
                {
                    cout << "could not parse \"" << key << "\" with value \"" << strvalue << "\"" << endl;
                }
            }
        }
    }

    if(!config_exists)
    {
        cout << "error: config file could not be found. You need to specify the path to it as command line argument" << endl;
        return 1;
    }

    if(raspberry_ip == "")
    {
        cout << "error: you need to set the raspberries ip in the config file like this (example): \"raspberry_ip=192.168.1.100\"" << endl;
        return 1;
    }

    // generate id for this client. no need for random, as this
    // random function is called only once, so i can just go ahead
    // and use the seed itself, which is time
    struct timeval seed;
    gettimeofday(&seed, NULL);
    int client_id = seed.tv_usec;

    // controls the resolution of the color space of the leds
    // default is 256, this is also configured in server.py
    // have this as float, because r, g and b are floats during
    // filtering in order to improve type compatibility stuff.
    const float full_on = 20000;

    // some checking for broken configurations
    if(lines == 0)
        lines = 1;
    if(columns == 0)
        columns = 1;
    if(checks_per_second == 0)
        checks_per_second = 1;
    if(linear_smoothing)
        // for linear smoothing it needs to be 1 at least
        // because it uses an array that contains at least
        // the new color
        smoothing = max(1, smoothing);
    else
        // otherwise, put 0 weight onto the old color
        smoothing = max(0, smoothing);

    XColor c;
    Display *d = XOpenDisplay((char *) NULL);
    Window root = XRootWindow(d, XDefaultScreen(d));
    Colormap colormap = XDefaultColormap(d, XDefaultScreen(d));

    XImage *image;

    // used for non-linear ease-out smoothing
    // and for checking if the color even changed
    // so save raspberry cpu time and network
    // bandwidth
    float r_old = 0;
    float g_old = 0;
    float b_old = 0;

    // used for linear smoothing
    // paranthesis will initialize the array with zeros
    float *r_window = new float[smoothing]();
    float *g_window = new float[smoothing]();
    float *b_window = new float[smoothing]();
    // i is the current po
    int i = 0;

    // assume a working condition in the beginning,
    // this is passed to sendcolor as a pointer and overwritten there
    // on successful communications
    long last_message_timestamp = get_us();

    // loop forever, reading the screen
    while(true)
    {

        long start = get_us();

        // work on floats in order to prevent rounding errors that add up
        float r = 1;
        float g = 1;
        float b = 1;

        // count three lines on the screen or something
        for(int i = 1;i <= lines;i++)
        {
            // to prevent overflows, aggregate color for each line individually
            // EDIT: that was needed when those variables were ints a long time ago
            double r_line = 0;
            double g_line = 0;
            double b_line = 0;
            double normalizer = 0;
            
            // ZPixmap fixes xorg color reading on cinnamon a little bit (as opposed to XYPixmap)
            // some info on XGetImage + XGetPixel speed:
            // asking for the complete screen: very slow
            // asking for lines: relatively fast
            // asking for individual pixels: slow
            int y = screen_height/(lines+1)*i;
            image = XGetImage(d, root, 0, y, screen_width, 1, AllPlanes, ZPixmap);
            
            // e.g. is columns is 3, it will check the center pixel, and the centers between the center pixel and the two borders
            for(int x = (screen_width%columns)/2;x < screen_width; x+=screen_width/columns)
            {
                c.pixel = XGetPixel(image, x, 0);
                XQueryColor(d, colormap, &c);
                // c contains colors that are by the factor 256 too large in their number.
                // When full_on is e.g. 256, then this formular will result in:
                // 255 * c.red / 256 / 256  =  1 * c.red / 256
                // for full_on = 2048 this is: 8 * c.red / 256
                int c_r = full_on * c.red / 256 / 256;
                int c_g = full_on * c.green / 256 / 256;
                int c_b = full_on * c.blue / 256 / 256;
                // give saturated colors (like green, purple, blue, orange, ...) more weight
                // over grey colors
                // difference between lowest and highest value should do the trick already
                int diff = ((max(max(c_r, c_g), c_b) - min(min(c_r, c_g), c_b)));
                double weight = diff * 20 / full_on + 1; // between 1 and 21
                normalizer += weight;
                r_line += c_r * weight;
                g_line += c_g * weight;
                b_line += c_b * weight;
            }

            // free up memory to prevent leak
            XFree(image);

            r += r_line / normalizer;
            g += g_line / normalizer;
            b += b_line / normalizer;
        }

        // r g and b are now between 0 and full_on
        r = r / lines;
        g = g / lines;
        b = b / lines;
        if(verbose_level >= 2) cout << "observed color  : " << r << " " << g << " " << b << endl;

        // only do stuff if the color changed.
        // the server only fades when the new color exceeds a threshold of 2.5% of full_on
        // in the added deltas. to not waste computational power of the pi and network bandwith,
        // do nothing.
        float delta_clr = abs(r - r_old) + abs(g - g_old) + abs(b - b_old);
        if(delta_clr > full_on * 0.025)
        {
            // don't overreact to sudden changes
            if(smoothing > 0)
            {
                if(linear_smoothing)
                {
                    // average of the last <smoothing> colors
                    r_window[i%smoothing] = r;
                    g_window[i%smoothing] = g;
                    b_window[i%smoothing] = b;
                    r = 0;
                    g = 0;
                    b = 0;
                    for(int w = 0; w < smoothing; w ++)
                    {
                        r += r_window[w];
                        g += g_window[w];
                        b += b_window[w];
                    }
                    r = r / smoothing;
                    g = g / smoothing;
                    b = b / smoothing;
                }
                else
                {
                    // converge on the new color
                    r = (r_old * smoothing + r) / (smoothing + 1);
                    g = (g_old * smoothing + g) / (smoothing + 1);
                    b = (b_old * smoothing + b) / (smoothing + 1);
                }

                if(verbose_level >= 2) cout << "smoothed color  : " << r << " " << g << " " << b << endl;
            }

            // make sure to do this directly after the smoothing
            // 1. to not break non-linear smoothing
            // 2. because smoothing should not be stopped when
            // the screen color doesn't change between checks
            r_old = r;
            g_old = g;
            b_old = b;

            // increase distance between darkest
            // and lightest channel in order to
            // increase saturation
            if(increase_saturation > 0)
            {
                float min_val = min(min(r, g), b);
                float old_max = max(max(r, g), b);
                r -= min_val * increase_saturation;
                g -= min_val * increase_saturation;
                b -= min_val * increase_saturation;
                // max with 1 to prevent division by zero
                float new_max = max((float)1, max(max(r, g), b));
                // normalize to old max value
                r = r * old_max / new_max;
                g = g * old_max / new_max;
                b = b * old_max / new_max;
                if(verbose_level >= 2) cout << "saturated color : " << r << " " << g << " " << b << endl;
            }

            if(normalize > 0)
            {
                // normalize it so that the lightest value is e.g. full_on
                // max with 1 to prevent division by zero
                float old_max;
                if(normalize_sum) old_max = r + g + b;
                else old_max = max(max(r, g), b);
                old_max = max(0.0f, old_max);
                if(old_max >= 0)
                {
                    float new_max = full_on;
                    r = r * (1 - normalize) + r * new_max / old_max * normalize;
                    g = g * (1 - normalize) + g * new_max / old_max * normalize;
                    b = b * (1 - normalize) + b * new_max / old_max * normalize;
                }
                if(verbose_level >= 2) cout << "normalized color: " << r << " " << g << " " << b << endl;
            }

            // correct led color temperature
            // 1. gamma
            if(gamma[0] > 0) r = pow(r / full_on, 1 / gamma[0]) * full_on;
            if(gamma[1] > 0) g = pow(g / full_on, 1 / gamma[1]) * full_on;
            if(gamma[2] > 0) b = pow(b / full_on, 1 / gamma[2]) * full_on;
            // 2. brightness
            r = r * brightness[0];
            g = g * brightness[1];
            b = b * brightness[2];
            // 3. clip into color range
            r = min(full_on, max(0.0f, r));
            g = min(full_on, max(0.0f, g));
            b = min(full_on, max(0.0f, b));
            if(verbose_level >= 2) cout << "temperature fix : " << r << " " << g << " " << b << endl;


            // for VERY dark colors, make it more gray to prevent supersaturated colors like (0, 1, 0).
            float darkness = (float)((r_old + g_old + b_old) / 3) / full_on;
            float greyscaling = max(0.0f, min(0.085f, darkness) / 0.085f);
            if(greyscaling < 1)
            {
                // for super dark colors, just use gray
                if(darkness < 0.01)
                    greyscaling = 0;
                // make dark colors more grey
                float mean = (r + g + b) / 3;
                r = (greyscaling) * r + (1 - greyscaling) * mean;
                g = (greyscaling) * g + (1 - greyscaling) * mean;
                b = (greyscaling) * b + (1 - greyscaling) * mean;
                if(verbose_level >= 2) cout << "dark color fix  : " << r << " " << g << " " << b << endl;
            }

            // send to the server for the illumination of the LEDs
            sendcolor((int)r, (int)g, (int)b, (char *)raspberry_ip.c_str(), raspberry_port, checks_per_second, client_id, SCREEN_COLOR, max_timeout, &last_message_timestamp, verbose_level);
        }
        else
        {
            if(verbose_level >= 1) cout << "color did not change or is too identical; skipping" << endl;
        }

        // 1000000 is one second
        // this of course greatly affects performance
        // don't only look for the server executable in your cpu usage,
        // also look for /usr/lib/Xorg cpu usage
        int delta = get_us() - start;
        if(verbose_level >= 1) cout << "calculating and sending: " << delta << "us" << endl;
        if(verbose_level >= 2) cout << endl;
        // try to check the screen colors once every second (or whatever the checks_per_second param is)
        // so substract the delta or there might be too much waiting time between each check
        usleep(max(0, 1000000 / checks_per_second - delta));

        // increment i, used for creating the window of colors for smoothing
        i ++;
    }

    return 0;
}

