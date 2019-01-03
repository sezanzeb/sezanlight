#include <iostream>
#include <unistd.h>
#include <math.h>

// many thanks to:
// https://stackoverflow.com/questions/53688777/how-to-implement-x11return-colour-of-a-screen-pixel-c-code-for-luajits-ffi
// https://kukuruku.co/post/a-cheat-sheet-for-http-libraries-in-c/
// https://stackoverflow.com/questions/9786150/save-curl-content-result-into-a-string-in-c
// https://stackoverflow.com/questions/19555121/how-to-get-current-timestamp-in-milliseconds-since-1970-just-the-way-java-gets
// https://stackoverflow.com/questions/7868936/read-file-line-by-line-using-ifstream-in-c#7868998
// https://stackoverflow.com/questions/3578083/what-is-the-best-way-to-use-a-hashmap-in-c
// https://stackoverflow.com/questions/216823/whats-the-best-way-to-trim-stdstring

#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <curl/curl.h>
#include <sys/time.h>
#include <fstream>
#include <sstream>
#include <boost/algorithm/string.hpp>

// color modes
#define SCREEN_COLOR 1
#define STATIC 2

// error codes
#define OK = "1"
#define ERROR "0"
#define CLOSE "2"

// for how long was no answer received from the server?
float timeout = 0;

// bad practice apparently:
using namespace std;

long int get_us()
{
    struct timeval time;
    gettimeofday(&time, NULL);
    long int us = time.tv_sec * 1000000 + time.tv_usec;
    return us;
}

static size_t WriteCallback(void *contents, size_t size, size_t nmemb, void *userp)
{
    ((string*)userp)->append((char*)contents, size *nmemb);
    return size *nmemb;
}

void sendcolor(int r, int g, int b, char *ip, int port, int checks_per_second, int client_id, int mode)
{
    CURL *curl;

    int handle_count;
    int max_timeout = 5;

    curl = curl_easy_init();
    if(curl)
    {
        char url[100];
        sprintf(url, "%s:%d?r=%d&g=%d&b=%d&cps=%d&id=%d&mode=%d", ip, port, r, g, b, checks_per_second, client_id, mode);
        cout << "sending GET pramas: " << url << "\n";

        long int start = get_us();
        string readBuffer;
        curl_easy_setopt(curl, CURLOPT_URL, url);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, max_timeout);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);
        CURLcode status = curl_easy_perform(curl);
        curl_easy_cleanup(curl);

        if(readBuffer == CLOSE)
        {
            cout << "server closed connection with this client to prevent duplicate connections. Another client started sending to the server!" << endl;
            exit(1);
        }

        // check if server is available if for 5 seconds no color reached it
        if(status != CURLE_OK)
        {
            // one check every 1/cps seconds, so add that as well
            int delta = (get_us() - start)/1000000;
            timeout += delta + 1.0/checks_per_second;
            if(timeout >= max_timeout) // 5 seconds timeout
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
            timeout = 0;
        }
    }
}

void parse_float_array(string strvalue, int size, float *array)
{
    // more complicated stuff, one float per channel in array
    int channel = 0;
    int j = 0;
    while(true)
    {
        if(strvalue[j] == ',' or strvalue[j] == '\0')
        {
            cout << channel << endl;
            float value = atof(strvalue.substr(0, j).c_str());
            array[channel] = value;
            channel ++;
        }
        j++;
        if(strvalue[j] != '\0') break;
    }
}

int main(void)
{
    // default params:

    // screen
    int screen_width = 1920;
    int screen_height = 1080;

    // sampling
    int smoothing = 6;
    int checks_per_second = 2;
    int columns = 100;
    int lines = 3;

    // hardware
    string raspberry_ip = "";
    int raspberry_port = 3546;

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
    // setting it to true will basically favor saturated colors over grey ones during normalization
    bool normalize_sum = true;
    // 0 = no adjustment, 0.5 = increases saturation, 1 = darkest color becomes 0 (prevents gray values alltogether)
    float increase_saturation = 0.67;

    // try to prevent suddenly jumping colors when
    // changing from e.g. <10, 11, 10> to <10, 10, 10>
    // if below this level, set to black
    int black_threshold = 30;

    // overwrite default params with params from config file
    ifstream infile("../config");
    string line;
    while (std::getline(infile, line))
    {
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
                    else if(key == "black_threshold") black_threshold = stoi(strvalue);
                }
                catch (invalid_argument e)
                {
                    cout << "could not parse \"" << key << "\" with value \"" << strvalue << "\"" << endl;
                }
            }
        }
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
    unsigned int full_on = 20000;

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
    unsigned int r_old = 0;
    unsigned int g_old = 0;
    unsigned int b_old = 0;

    // used for linear smoothing
    // paranthesis will initialize the array with zeros
    unsigned int *r_window = new unsigned int[smoothing]();
    unsigned int *g_window = new unsigned int[smoothing]();
    unsigned int *b_window = new unsigned int[smoothing]();

    int i = 0;

    // loop forever, reading the screen
    while(true)
    {

        long int start = get_us();

        unsigned int r = 1;
        unsigned int g = 1;
        unsigned int b = 1;

        // count three lines on the screen or something
        for(int i = 1;i <= lines;i++)
        {
            // to prevent overflows, aggregate color for each line individually
            unsigned long int r_line = 0;
            unsigned long int g_line = 0;
            unsigned long int b_line = 0;
            float normalizer = 0;
            
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
                unsigned int c_r = full_on * c.red / 256 / 256;
                unsigned int c_g = full_on * c.green / 256 / 256;
                unsigned int c_b = full_on * c.blue / 256 / 256;
                // give saturated colors (like green, purple, blue, orange, ...) more weight
                // over grey colors
                // difference between lowest and highest value should do the trick already
                int diff = ((max(max(c_r, c_g), c_b) - min(min(c_r, c_g), c_b)));
                // and also favor light ones over dark ones
                int lightness = (c_r + c_g + c_b)/3;
                // lightness and diff are between 0 and full_on
                float weight = (float)(diff + lightness)/2/128 + 1; // between 1 and 16 (full_on/128)
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
        r = r/lines;
        g = g/lines;
        b = b/lines;
        cout << "observed color  : " << r << " " << g << " " << b << endl;

        // only do stuff if the color changed.
        // If the smoothed color (*_old) is equal to the observed color,
        // skip
        if(r != r_old and g != g_old and b != b_old)
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

                cout << "smoothed color  : " << r << " " << g << " " << b << endl;
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
                unsigned int min_val = min(min(r, g), b);
                unsigned int old_max = max(max(r, g), b);
                r -= min_val * increase_saturation;
                g -= min_val * increase_saturation;
                b -= min_val * increase_saturation;
                // max with 1 to prevent division by zero
                unsigned int new_max = max(1u, max(max(r, g), b));
                // normalize to old max value
                r = r * old_max / new_max;
                g = g * old_max / new_max;
                b = b * old_max / new_max;
                cout << "saturated color : " << r << " " << g << " " << b << endl;
            }

            if(normalize > 0)
            {
                // normalize it so that the lightest value is e.g. full_on
                // max with 1 to prevent division by zero
                unsigned int old_max;
                if(normalize_sum) old_max = r + g + b;
                else old_max = max(max(r, g), b);
                old_max = max(1u, old_max);
                if(old_max >= 0)
                {
                    int new_max = full_on;
                    r = r * (1 - normalize) + r * new_max / old_max * normalize;
                    g = g * (1 - normalize) + g * new_max / old_max * normalize;
                    b = b * (1 - normalize) + b * new_max / old_max * normalize;
                }
                cout << "normalized color: " << r << " " << g << " " << b << endl;
            }

            // correct led color temperature
            // 1. gamma
            if(gamma[0] > 0) r = (pow((float)r / full_on, 1 / gamma[0]) * full_on);
            if(gamma[1] > 0) g = (pow((float)g / full_on, 1 / gamma[1]) * full_on);
            if(gamma[2] > 0) b = (pow((float)b / full_on, 1 / gamma[2]) * full_on);
            // 2. brightness
            r = (r * brightness[0]);
            g = (g * brightness[1]);
            b = (b * brightness[2]);
            // 3. clip into color range
            r = min(full_on, max(0u, r));
            g = min(full_on, max(0u, g));
            b = min(full_on, max(0u, b));
            cout << "filtered color  : " << r << " " << g << " " << b << endl;

            // turn off leds for values that are too dark
            if(r+g+b < black_threshold*3)
            {
                r = 0;
                g = 0;
                b = 0;
                cout << "setting to black" << endl;
            }

            // send to the server for display
            sendcolor(r, g, b, (char *)raspberry_ip.c_str(), raspberry_port, checks_per_second, client_id, SCREEN_COLOR);
        }
        else
        {
            cout << "color did not change; skipping" << endl;
        }

        // 1000000 is one second
        // this of course greatly affects performance
        // don't only look for the server executable in your cpu usage,
        // also look for /usr/lib/Xorg cpu usage
        int delta = get_us() - start;
        cout << "calculating and sending: " << delta << "us" << endl;
        cout << endl;
        // try to check the screen colors once every second (or whatever the checks_per_second param is)
        // so substract the delta or there might be too much waiting time between each check
        usleep(max(0, 1000000 / checks_per_second - delta));

        // increment i, used for creating the window of colors for smoothing
        i ++;
    }

    return 0;
}

