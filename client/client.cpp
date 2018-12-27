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
    // configuration
    int width = 1920;
    int height = 1080;
    bool normalize = false;
    bool increase_saturation = true;
    int smoothing = 1;
    int checks_per_second = 1;
    int columns = 50;
    int lines = 5;
    char raspberry_ip[15] = "192.168.2.110";
    int raspberry_port = 8000;

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

    int r_old = 0;
    int g_old = 0;
    int b_old = 0;

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
                float weight = (float)(diff + lightness)/2/64 + 1; // between 1 and 5
                normalizer += weight;
                r_line += (int)(c_r * weight);
                g_line += (int)(c_g * weight);
                b_line += (int)(c_b * weight);
            }

            r += r_line / (int)normalizer;
            g += g_line / (int)normalizer;
            b += b_line / (int)normalizer;
        }

        // r g and b are now between 0 and full_on
        r = r/lines;
        g = g/lines;
        b = b/lines;

        cout << "observed color  : " << r << " " << g << " " << b << endl;

        if(increase_saturation)
        {
            // increase distance between darkest
            // and lightest channel
            int min_val = min(min(r, g), b);
            int old_max = max(max(r, g), b);
            r -= min_val * 2 / 3;
            g -= min_val * 2 / 3;
            b -= min_val * 2 / 3;
            // max with 1 to prevent division by zero
            int new_max = max(1, max(max(r, g), b));
            // normalize to old max value
            r = r*old_max/new_max;
            g = g*old_max/new_max;
            b = b*old_max/new_max;
            cout << "saturated color : " << r << " " << g << " " << b << endl;
        }

        if(normalize)
        {
            // normalize it so that the lightest value is e.g. full_on
            // the leds are quite cold, so make the color warm
            // max with 1 to prevent division by zero
            int old_max = max(1, max(max(r, g), b));
            int new_max = full_on;
            r = r*new_max/old_max;
            g = g*new_max/old_max;
            b = b*new_max/old_max;
            cout << "normalized color: " << r << " " << g << " " << b << endl;
        }

        // don't overreact to sudden changes
        r = (r_old * smoothing + r)/(smoothing + 1);
        g = (g_old * smoothing + g)/(smoothing + 1);
        b = (b_old * smoothing + b)/(smoothing + 1);
        r_old = r;
        g_old = g;
        b_old = b;

        // last step: correct led color temperature
        // 1. gamma
        g = (int)(pow((float)g/full_on, 1.2)*full_on);
        b = (int)(pow((float)b/full_on, 1.3)*full_on);
        // 2. lightness
        g = g * 10 / 13;
        b = b * 10 / 17;
        // red remains the same
        cout << "warmer color    : " << r << " " << g << " " << b << endl;

        // send to the server for display
        sendcolor(r, g, b, raspberry_ip, raspberry_port, checks_per_second);

        // free up memory to prevent leak
        XFree(image);

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
    }

    return 0;
}
