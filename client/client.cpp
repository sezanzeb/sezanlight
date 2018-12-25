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

        // count three lines on the screen or something
        for(int i = 1;i < 3;i++)
        {
            image = XGetImage(d, XRootWindow (d, XDefaultScreen(d)), 0, height/3*i, width, 1, AllPlanes, XYPixmap);
            for(int x = 0;x < width; x+=width/100)
            {
                c.pixel = XGetPixel(image, x, 0);
                XQueryColor(d, XDefaultColormap(d, XDefaultScreen(d)), &c);
                r += c.red;
                g += c.green;
                b += c.blue;
            }
        }

        // normalize it so that the lightest value is 255 and the darkest 0
        int min_val = min(min(r, g), b);
        r -= min_val;
        g -= min_val;
        b -= min_val;
        int max_val = max(max(r, g), b);
        r = r*255/max_val;
        g = g*255/max_val;
        b = b*255/max_val;

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
