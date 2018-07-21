#ifndef SERVER_H
#define SERVER_H

#include <winsock2.h>

class Server
{
private:
    char server_port[6];
public:
    Server(char* port);
    int run();
    ~Server();
};

#endif // SERVER_H
