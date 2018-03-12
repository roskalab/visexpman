#ifndef MESCAPIHANDLER_H
#define MESCAPIHANDLER_H

#define MESC_NO_ERROR 0
#define MESC_INVALID_COMMAND 4

#include <QLibrary>

#include "ReplyMessageParser.h"

#include "APIClientManager.h"

#include "ClientListModel.h"

class MescApiHandler
{
private:
    APIClientManager *pClientManager;
public:
    MescApiHandler();
    int send(char* command, char* response);
    ~MescApiHandler();
};

#endif // MESCAPIHANDLER_H
