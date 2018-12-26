#include <iostream>
#include <unistd.h>

// many thanks to:
// https://stackoverflow.com/questions/53688777/how-to-implement-x11return-colour-of-a-screen-pixel-c-code-for-luajits-ffi
#include <X11/Xlib.h>
#include <X11/Xutil.h>

// https://kukuruku.co/post/a-cheat-sheet-for-http-libraries-in-c/
// https://stackoverflow.com/questions/9786150/save-curl-content-result-into-a-string-in-c
#include <curl/curl.h>

// https://stackoverflow.com/questions/19555121/how-to-get-current-timestamp-in-milliseconds-since-1970-just-the-way-java-gets
#include <sys/time.h>

// https://stackoverflow.com/questions/10820377/c-format-char-array-like-printf

using namespace std;

static size_t WriteCallback(void *contents, size_t size, size_t nmemb, void *userp)
{
    ((string*)userp)->append((char*)contents, size * nmemb);
    return size * nmemb;
}

void sendcolor(int r, int g, int b, char * ip, int port)
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
        sprintf(url, "%s:%d?r=%d&g=%d&b=%d", ip, port, r, g, b);
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
    bool normalize = true;
    bool increase_saturation = true;
    int checks_per_second = 1;
    int columns = 100;
    int lines = 10;
    char raspberry_ip[15] = "192.168.2.110";
    int raspberry_port = 8000;

    XColor c;
    Display *d = XOpenDisplay((char *) NULL);

    XImage *image;

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
            int normalizer = 0;
            
            image = XGetImage(d, XRootWindow (d, XDefaultScreen(d)), 0, height/(lines+1)*i, width, 1, AllPlanes, XYPixmap);
            
            // e.g. is columns is 3, it will check the center pixel, and the centers between the center pixel and the two borders
            for(int x = (width%columns)/2;x < width; x+=width/columns)
            {
                c.pixel = XGetPixel(image, x, 0);
                XQueryColor(d, XDefaultColormap(d, XDefaultScreen(d)), &c);
                // give saturated colors (like green, purple, blue, orange, ...) more weight
                // over grey colors
                // difference between lowest and highest value should do the trick already
                // divide by 2^10 (bitshift 10) to avoid int overflows
                int diff = ((max(max(c.red, c.green), c.blue) - min(min(c.red, c.green), c.blue)) >> 10) + 1;
                // and also favor light ones over dark ones
                int lightness = max(max(c.red, c.green), c.blue) >> 10;
                int weight = diff + lightness;
                normalizer += weight;
                r_line += c.red * weight;
                g_line += c.green * weight;
                b_line += c.blue * weight;
            }

            r += r_line / normalizer;
            g += g_line / normalizer;
            b += b_line / normalizer;

        }

        // make the darkest color even darker
        // to increase saturation
        int min_val = min(min(r, g), b);
        r -= min_val >> 2;
        g -= min_val >> 2;
        b -= min_val >> 2;

        // normalize it so that the lightest value is 255
        // the leds are quite cold, so make the color warm
        int max_val = max(max(r, g), b);
        r = r*255/max_val;
        g = g*200/max_val;
        b = b*150/max_val;

        // send to the server for display
        sendcolor(r, g, b, raspberry_ip, raspberry_port);

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
        cout << delta << endl;
        // try to check the screen colors once every second (or whatever the checks_per_second param is)
        // so substract the delta or there might be too much waiting time between each check
        usleep(max(0, 1000000/checks_per_second - delta));
    }

    return 0;
}
