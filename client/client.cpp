#include <iostream>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <time.h>
#include <unistd.h>

// many thanks to:
// https://stackoverflow.com/questions/53688777/how-to-implement-x11return-colour-of-a-screen-pixel-c-code-for-luajits-ffi

using namespace std;

int main(int, char**)
{
    int iter1 = 1000;
    int iter2 = 20;
    int y = 500;

    int width = 1920;
    int height = 1080;

    XColor c;
    Display *d = XOpenDisplay((char *) NULL);

    XImage *image;

    for(int i = 0;i < iter1; i++)
    {
        // XGetImage seems to be rather slow
        // but it's the fastest solution i have come across
        
        // to make it even faster, ask for a single lines instead of a lot of points to reduce number of calls.
        // asking for lines also makes it quite flexible in where to place lines for color checks.
        // Asking for the whole screen is slow again.

        image = XGetImage(d, XRootWindow (d, XDefaultScreen(d)), 0, y, 1920, 1, AllPlanes, XYPixmap);
        int r = 0;
        int g = 0;
        int b = 0;
        for(int x = 0;x < width; x+=width/10)
        {
            c.pixel = XGetPixel(image, x, 0);
            XQueryColor(d, XDefaultColormap(d, XDefaultScreen(d)), &c);
            r += c.red;
            g += c.green;
            b += c.blue;
        }
        // average color
        r = (float)r/iter2;
        g = (float)g/iter2;
        b = (float)b/iter2;
        // normalize it so that the lightest value is 255
        int max_val = max(max(r, g), b);
        r = r*255/max_val;
        g = g*255/max_val;
        b = b*255/max_val;
        cout << "r: " << r << " g: " << g << " b: " << b << "\n";
        XFree(image);

        // 1000000 is one second
        // this of course greatly affects performance
        // don't only look for the server executable in your cpu usage,
        // also look for /usr/lib/Xorg cpu usage
        // 4 checks per second keeps it at 3% on my i5
        usleep(1000000/4);
    }

    return 0;
}
