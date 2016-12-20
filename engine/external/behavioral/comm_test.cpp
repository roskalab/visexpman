#include "comm.h"
#include <iostream>
#include <string.h>
using namespace std;

void test(Comm* c, int id)
{
    int res;
    cout<<"=== test "<<id<<" ===\r\nbuffer's content:\r\n====";
    cout<<c->buffer;
    cout<<"====\r\n";
    res=c->parse();
    cout<<"result: "<<res<<" | cmd: "<<c->command<<" | n params: "<<c->nparams<<" | ";
    for(int i=0;i<c->nparams;i++)
    {
        cout<<c->par[i]<<" ";
    }
    cout<<endl;
}

int main(void)
{
    char str[100];
    memset(str,0,100);

    strcpy(str,"testcmd1,10,123,4,11.1,1,2,509.0\r\ntestcmd2\r\ntestcmd3");
    cout << "Running tests... \r\n";
    Comm c=Comm();
    c.put(str);
    memset(str,0,100);
    strcpy(str,"testcmd4,5\r\n");
    c.put(str);

    test(&c,1);
    test(&c,2);
    test(&c,3);
    test(&c,4);

    memset(str,0,100);
    strcpy(str,"testcmd5,100.5\r\n");
    c.put(str);
    test(&c,5);
    memset(str,0,100);
    strcpy(str,"testcmd6,100.5,1testcmd7,20\r\n");
    c.put(str);
    test(&c,6);
    test(&c,7);
	return 0;
}
