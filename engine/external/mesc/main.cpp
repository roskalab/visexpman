#include <QCoreApplication>
#include <string.h>
#include "server.h"

#include <winsock2.h>
int main(int argc, char *argv[])
{
    QCoreApplication a(argc, argv);
    Server *s= new Server(argv[1]);
    s->run();
    delete s;
    return 0;//a.exec();
}


