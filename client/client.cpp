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
    ((std::string*)userp)->append((char*)contents, size * nmemb);
    return size * nmemb;
}

void sendcolor(int r, int g, int b)
{
    CURL *curl;
    CURLcode res;
    std::string readBuffer;

    curl = curl_easy_init();
    if(curl)
    {
        char url[100]; // change to 32 once working
        sprintf(url, "192.168.2.110:8000?r=%d&g=%d&b=%d", r, g, b);
        cout << url << "\n";

        curl_easy_setopt(curl, CURLOPT_URL, url);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);
        res = curl_easy_perform(curl);
        curl_easy_cleanup(curl);

        std::cout << readBuffer << std::endl;
    }
}

int main(int, char**)
{
    int width = 1920;
    int height = 1080;

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

        int lines = 3;

        // count three lines on the screen or something
        for(int i = 1;i <= lines;i++)
        {
            // to prevent overflows, aggregate color for each line individually
            int r_line = 0;
            int g_line = 0;
            int b_line = 0;
            int normalizer = 0;
            
            image = XGetImage(d, XRootWindow (d, XDefaultScreen(d)), 0, height/(lines+1)*i, width, 1, AllPlanes, XYPixmap);
            
            for(int x = 0;x < width; x+=width/150)
            {
                c.pixel = XGetPixel(image, x, 0);
                XQueryColor(d, XDefaultColormap(d, XDefaultScreen(d)), &c);
                // give saturated colors (like green, purple, blue, orange, ...) more weight
                // over grey colors
                // difference between lowest and highest value should do the trick already
                // divide by 2^10 (bitshift 10) to avoid int overflows
                int diff = ((max(max(c.red, c.green), c.blue) - min(min(c.red, c.green), c.blue)) >> 10) + 1;
                // and also favor light ones over dark ones
                int lightness = (c.red + c.green + c.blue) >> 10;
                int weight = diff + lightness;
                normalizer += weight;
                r_line += c.red * weight;
                g_line += c.green * weight;
                b_line += c.blue * weight;
                // cout << "d:" << diff << " l:" << lightness << " w:" << weight << " r:" << r << " g:" << g << " b:" << b << "\n";
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

        // i feel like the leds are quite cold
        // so instead of 256, i divide b by 300
        /*r = r/normalizer/256;
        g = g/normalizer/256;
        b = b/normalizer/300;*/

        // cout << r << " " << g << " " << b << "\n";

        // send to the server for display
        sendcolor(r, g, b);

        // free up memory to prevent leak
        XFree(image);

        // 1000000 is one second
        // this of course greatly affects performance
        // don't only look for the server executable in your cpu usage,
        // also look for /usr/lib/Xorg cpu usage
        // 4 checks per second keeps it at 3% on my i5
        usleep(1000000/1);
    }

    return 0;
}
