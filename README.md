# MSynth Paint- A draw pad that turns pixel art into sounds
A small program developed in Python meant to be a fun representation of a digital to analog converter (DAC). DACs are typically physical hardware that
may include some firmware that drive the conversion of digitally stored data into an analog signal that is able to be passed through low level electronics such
as speakers, as well as be read by oscilloscopes for diagnosing data loss. This is typically encountered in the form of music players such as an iPod, but any
device with a speaker that plays sounds has a DAC within.

## Drawings into music!
I used the tkinter library to create a basic drawing app similar to a very old iteration of MS Paint with a 128x128 pixel canvas. This was done for simplicity of
pixel data collection, to keep the .JSON file storing the data small, and also because I really like pixel art. You simply draw on the canvas, and I would suggest
using a few different colors, and when finished you can export the drawing to the 'synthesizer' to play it as music.

## How it works
The program hosts a draw pad by creating an array of pixels (128x128) holding 3 integer values from 0-255 in the classic RGB format. The position of each pixel is
stored in a 2-D list, `self.pixels[y][x]`, in row-major order. This allows for the data to be parsed in various directions (i.e. left to right or right to left),
without needing to restructure the list. Each element of the list is a 3-tuple, a variable which stores multiple items, in this case 3 integers for R, G, and B.
Each row in the list is independently allocated to prevent a chain of mutation exploding out from each row. The tkinter library allows the creation of the canvas, and
each 'pixel' on the draw pad is actually a collection of pixels on the screen, since monitor resolutions are so high having it actually be 128x128 would be too small
to work with. The coordinates of the mouse click are temporarily stored, and compared to a cell index to determine where the color gets filled in. When the drawing is
exported to the synthesizer program, the RGB data of each pixel is condensed into one single integer. This is done to decrease the complexity of the data, changing it
from an object to a simple integer ranging from 0-765, and is stored in a .JSON file for simplicity. This integer is then used in the DAC driver to create a tone on a laptop speaker using the RGB composite integer
as the value for the frequency of the tone in Hz. The data is also saved in row order, so each element of the .JSON is one row, which allows us to parse it easily in
different directions. Now we have a tone frequency and an order to output those frequencies. The DAC driver passes an analog signal to your devices speakers, converting
your image into a range of tones that is almost musical! This is best done with a very spread out and multicolored piece, causing a range of tones to play at different
points.
