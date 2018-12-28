#include <iostream>
#include <unistd.h>
#include <math.h>

// many thanks to:
// https://stackoverflow.com/questions/53688777/how-to-implement-x11return-colour-of-a-screen-pixel-c-code-for-luajits-ffi
#include <X11/Xlib.h>
#include <X11/Xutil.h>

// https://kukuruku.co/post/a-cheat-sheet-for-http-libraries-in-c/
// https://stackoverflow.com/questions/9786150/save-curl-content-result-into-a-string-in-c
#include <curl/curl.h>

// https://stackoverflow.com/questions/19555121/how-to-get-current-timestamp-in-milliseconds-since-1970-just-the-way-java-gets
#include <sys/time.h>


using namespace std;

static size_t WriteCallback(void *contents, size_t size, size_t nmemb, void *userp)
{
    ((string*)userp)->append((char*)contents, size * nmemb);
    return size * nmemb;
}

void sendcolor(int r, int g, int b, char * ip, int port, int checks_per_second)
{
    CURL *curl;
    CURLcode res;

    CURLM *multi_handle;
    multi_handle = curl_multi_init();
    int handle_count;

    curl = curl_easy_init();
    if(curl)
    {
        char url[100];
        sprintf(url, "%s:%d?r=%d&g=%d&b=%d&cps=%d", ip, port, r, g, b, checks_per_second);
        cout << "sending GET pramas: " << url << "\n";

        curl_easy_setopt(curl, CURLOPT_URL, url);

        // in order to hide server response from console
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        string readBuffer;
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);
        // cout << readBuffer << endl;

        res = curl_easy_perform(curl);
        curl_easy_cleanup(curl);
    }
}

int main(void)
{
    // screen
    int width = 1920;
    int height = 1080;

    // sampling
    int smoothing = 6;
    int checks_per_second = 2;
    int columns = 100;
    int lines = 3;

    // hardware
    char raspberry_ip[15] = "192.168.2.110";
    int raspberry_port = 8000;

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




    // controls the resolution of the color space of the leds
    // default is 256, this is also configured in server.py
    int full_on = 2048;

    // some checking for broken configurations
    if(lines == 0)
        lines = 1;
    if(columns == 0)
        columns = 1;
    if(checks_per_second == 0)
        checks_per_second = 1;

    XColor c;
    Display *d = XOpenDisplay((char *) NULL);
    Window root = XRootWindow(d, XDefaultScreen(d));
    Colormap colormap = XDefaultColormap(d, XDefaultScreen(d));

    XImage *image;

    // used for non-linear ease-out smoothing
    int r_old = 0;
    int g_old = 0;
    int b_old = 0;

    // used for linear smoothing
    int r_window[smoothing] = {0, 0, 0};
    int g_window[smoothing] = {0, 0, 0};
    int b_window[smoothing] = {0, 0, 0};

    int i = 0;

    while(1)
    {
        // XGetImage in c++ is the fastest solution i have come across
        
        // to make it even faster, ask for a single lines instead of a lot of points to reduce number of calls.
        // asking for lines also makes it quite flexible in where to place lines for color checks.
        // Asking for the whole screen is slow again. At least it seemed like that

        struct timeval start;
        gettimeofday(&start, NULL);
        long int start_us = start.tv_sec * 1000000 + start.tv_usec;

        int r = 1;
        int g = 1;
        int b = 1;

        // count three lines on the screen or something
        for(int i = 1;i <= lines;i++)
        {
            // to prevent overflows, aggregate color for each line individually
            long int r_line = 0;
            long int g_line = 0;
            long int b_line = 0;
            float normalizer = 0;
            
            // was XYPixmap
            // ZPixmap fixes cinnamon
            image = XGetImage(d, root, 0, height/(lines+1)*i, width, 1, AllPlanes, ZPixmap);
            
            // e.g. is columns is 3, it will check the center pixel, and the centers between the center pixel and the two borders
            for(int x = (width%columns)/2;x < width; x+=width/columns)
            {
                c.pixel = XGetPixel(image, x, 0);
                XQueryColor(d, colormap, &c);
                // c contains colors that are by the factor 256 too large in their number
                // when full_on was the standard of 256, then this formular will result in:
                // 1*c.red/256
                // for full_on = 2048 this is: 8*c.red/256
                int c_r = (full_on/256)*c.red/256;
                int c_g = (full_on/256)*c.green/256;
                int c_b = (full_on/256)*c.blue/256;
                // give saturated colors (like green, purple, blue, orange, ...) more weight
                // over grey colors
                // difference between lowest and highest value should do the trick already
                int diff = ((max(max(c_r, c_g), c_b) - min(min(c_r, c_g), c_b)));
                // and also favor light ones over dark ones
                int lightness = (c_r + c_g + c_b)/3;
                // lightness and diff are between 0 and full_on
                float weight = (float)(diff + lightness)/2/64 + 1; // between 1 and 32 (full_on/64)
                normalizer += weight;
                r_line += (int)(c_r * weight);
                g_line += (int)(c_g * weight);
                b_line += (int)(c_b * weight);
            }

            // free up memory to prevent leak
            XFree(image);

            r += r_line / (int)normalizer;
            g += g_line / (int)normalizer;
            b += b_line / (int)normalizer;
        }

        // r g and b are now between 0 and full_on
        r = r/lines;
        g = g/lines;
        b = b/lines;
        cout << "observed color  : " << r << " " << g << " " << b << endl;

        if(increase_saturation > 0)
        {
            // increase distance between darkest
            // and lightest channel
            int min_val = min(min(r, g), b);
            int old_max = max(max(r, g), b);
            r -= min_val * increase_saturation;
            g -= min_val * increase_saturation;
            b -= min_val * increase_saturation;
            // max with 1 to prevent division by zero
            int new_max = max(1, max(max(r, g), b));
            // normalize to old max value
            r = (int)(r*old_max/new_max);
            g = (int)(g*old_max/new_max);
            b = (int)(b*old_max/new_max);
            cout << "saturated color : " << r << " " << g << " " << b << endl;
        }

        if(normalize > 0)
        {
            // normalize it so that the lightest value is e.g. full_on
            // max with 1 to prevent division by zero
            int old_max;
            if(normalize_sum) old_max = r + g + b;
            else old_max = max(max(r, g), b);
            old_max = max(1, old_max);
            if(old_max >= 0)
            {
                int new_max = full_on;
                r = r*(1-normalize) + r*new_max/old_max*normalize;
                g = g*(1-normalize) + g*new_max/old_max*normalize;
                b = b*(1-normalize) + b*new_max/old_max*normalize;
            }
            cout << "normalized color: " << r << " " << g << " " << b << endl;
        }

        // correct led color temperature
        // 1. gamma
        if(gamma[0] > 0) r = (int)(pow((float)r/full_on, 1/gamma[0])*full_on);
        if(gamma[1] > 0) g = (int)(pow((float)g/full_on, 1/gamma[1])*full_on);
        if(gamma[2] > 0) b = (int)(pow((float)b/full_on, 1/gamma[2])*full_on);
        // 2. brightness
        r = (int)(r * brightness[0]);
        g = (int)(g * brightness[1]);
        b = (int)(b * brightness[2]);
        // 3. clip into color range
        r = min(full_on, max(0, r));
        g = min(full_on, max(0, g));
        b = min(full_on, max(0, b));
        cout << "filtered color  : " << r << " " << g << " " << b << endl;

        // don't overreact to sudden changes
        if(smoothing > 0)
        {
            if(linear_smoothing)
            {
                r_window[i%smoothing] = r;
                g_window[i%smoothing] = g;
                b_window[i%smoothing] = b;
                // calculate average of window
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
                r = (r_old * smoothing + r)/(smoothing + 1);
                g = (g_old * smoothing + g)/(smoothing + 1);
                b = (b_old * smoothing + b)/(smoothing + 1);
                r_old = r;
                g_old = g;
                b_old = b;
            }

            cout << "smoothed color  : " << r << " " << g << " " << b << endl;
        }

        // turn off leds for values that are too dark
        if(r+g+b < black_threshold*3)
        {
            r = 0;
            g = 0;
            b = 0;
            cout << "setting to black" << endl;
        }

        // send to the server for display
        sendcolor(r, g, b, raspberry_ip, raspberry_port, checks_per_second);

        // 1000000 is one second
        // this of course greatly affects performance
        // don't only look for the server executable in your cpu usage,
        // also look for /usr/lib/Xorg cpu usage
        struct timeval end;
        gettimeofday(&end, NULL);
        long int end_us = end.tv_sec * 1000000 + end.tv_usec;
        int delta = (int)(end_us - start_us);
        cout << "calculating and sending: " << delta << "us" << endl;
        cout << endl;
        // try to check the screen colors once every second (or whatever the checks_per_second param is)
        // so substract the delta or there might be too much waiting time between each check
        usleep(max(0, 1000000/checks_per_second - delta));

        // increment i, used for creating the window of colors for smoothing
        i ++;
    }

    return 0;
}
