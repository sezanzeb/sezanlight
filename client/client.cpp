#include <iostream>
#include <unistd.h>

// many thanks to:
// https://stackoverflow.com/questions/53688777/how-to-implement-x11return-colour-of-a-screen-pixel-c-code-for-luajits-ffi
#include <X11/Xlib.h>
#include <X11/Xutil.h>

// https://kukuruku.co/post/a-cheat-sheet-for-http-libraries-in-c/
// https://stackoverflow.com/questions/9786150/save-curl-content-result-into-a-string-in-c
#include <curl/curl.h>

// https://stackoverflow.com/questions/10820377/c-format-char-array-like-printf

using namespace std;

static size_t WriteCallback(void *contents, size_t size, size_t nmemb, void *userp)
{
    ((string*)userp)->append((char*)contents, size * nmemb);
    return size * nmemb;
}

void sendcolor(int r, int g, int b, string adress)
{
    CURL *curl;
    CURLcode res;
    string readBuffer;

    curl = curl_easy_init();
    if(curl)
    {
        char url[100];
        sprintf(url, "%s?r=%d&g=%d&b=%d", adress, r, g, b);
        cout << "sending GET pramas: " << url << "\n";

        curl_easy_setopt(curl, CURLOPT_URL, url);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        // curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);
        res = curl_easy_perform(curl);
        curl_easy_cleanup(curl);

        // cout << readBuffer << endl;
    }
}

int main(int, char**)
{
    // configuration
    int width = 1920;
    int height = 1080;
    bool normalize = true;
    bool increase_saturation = true;
    int checks_per_second = 1;
    int columns = 50;
    int lines = 3;
    string raspberry_ip = "192.168.2.110";
    string raspberry_port = "8000";

    XColor c;
    Display *d = XOpenDisplay((char *) NULL);

    XImage *image;

    while(1)
    {
        // XGetImage seems to be rather slow
        // but it's the fastest solution i have come across
        
        // to make it even faster, ask for a single lines instead of a lot of points to reduce number of calls.
        // asking for lines also makes it quite flexible in where to place lines for color checks.
        // Asking for the whole screen is slow again.

        int r = 1;
        int g = 1;
        int b = 1;

        // count three lines on the screen or something
        for(int i = 1;i <= lines;i++)
        {
            // to prevent overflows, aggregate color for each line individually
            int r_line = 0;
            int g_line = 0;
            int b_line = 0;
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
        sendcolor(r, g, b, raspberry_ip + raspberry_port);

        // free up memory to prevent leak
        XFree(image);

        // 1000000 is one second
        // this of course greatly affects performance
        // don't only look for the server executable in your cpu usage,
        // also look for /usr/lib/Xorg cpu usage
        usleep(1000000/checks_per_second);
    }

    return 0;
}
