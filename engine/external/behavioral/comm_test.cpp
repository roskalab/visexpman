#include "comm.h"
#include <iostream>
#include <string.h>
using namespace std;

int main(void)
{
    char str[100];
    strcpy(str,"test,10,123,4,11.1,1,2,509.0\r\nsingle_cmd\r\n");
//    strcpy(str,"test,509.0\r\n");
    cout << "Running tests... \r\n";
    Comm c=Comm();
//    c.parse();
    c.put(str);
    strcpy(str,"test2,5\r\n");
//    c.put(str);
    c.parse();
//    cout << c.buffer;
	return 0;
}
