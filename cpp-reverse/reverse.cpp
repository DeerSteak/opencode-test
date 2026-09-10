#include <iostream>
#include <string>
#include <vector>
#include <termios.h>
#include <unistd.h>

static int readKey() {
    termios oldt, rawt;
    tcgetattr(STDIN_FILENO, &oldt);
    rawt = oldt;
    rawt.c_lflag &= ~(ICANON | ECHO);
    tcsetattr(STDIN_FILENO, TCSANOW, &rawt);
    char c = 0;
    read(STDIN_FILENO, &c, 1);
    tcsetattr(STDIN_FILENO, TCSANOW, &oldt);
    return c;
}

// Length in bytes of the UTF-8 code point starting at s, or 0 if malformed.
static int codePointLen(const unsigned char* s, size_t remaining) {
    unsigned char b = s[0];
    int n;
    if (b < 0x80)              n = 1;
    else if ((b & 0xE0) == 0xC0) n = 2;
    else if ((b & 0xF0) == 0xE0) n = 3;
    else if ((b & 0xF8) == 0xF0) n = 4;
    else return 0;
    if (static_cast<size_t>(n) > remaining) return 0;
    for (int i = 1; i < n; ++i)
        if ((s[i] & 0xC0) != 0x80) return 0;
    return n;
}

// Reverses whole code points, preserving each one's exact original bytes.
static std::string reverseUTF8(const std::string& s) {
    std::vector<std::string> cps;
    const unsigned char* p = reinterpret_cast<const unsigned char*>(s.data());
    size_t n = s.size(), i = 0;
    while (i < n) {
        int len = codePointLen(p + i, n - i);
        if (len == 0) len = 1; // malformed: keep byte as its own unit
        cps.push_back(s.substr(i, len));
        i += len;
    }
    std::string out;
    for (auto it = cps.rbegin(); it != cps.rend(); ++it)
        out += *it;
    return out;
}

int main() {
    std::string s;
    std::cout << "Enter a string: ";
    std::getline(std::cin, s);

    std::cout << "Reversed: " << reverseUTF8(s) << "\n";

    std::cout << "Press any key to exit..." << std::flush;
    readKey();

    return 0;
}