

#include "mescapihandler.h"
#include <string.h>

MescApiHandler::MescApiHandler()
{
    qDebug() << "START";

    pClientManager = new APIClientManager();

    bool ok = pClientManager->webSocketConnect(QUrl("ws://localhost:8888"));
    if (ok)
    {
        AbstractAPIClient * client= pClientManager->getClientListModel()->getClient(0);

        ReplyMessageParser *loginParser;
        loginParser=client ->login("userName", "Passwd123%");
        bool logins=false;
        if (loginParser->getResultCode()!=0) {
            qDebug() << loginParser->getErrorText();
        }
        else
        {
            logins=true;

        }

        qDebug() << "Connected, login:" << ok;


    }
    else
    {
        qDebug() << "Cannot connect";
    }
}

int MescApiHandler::send(char* command, char* response)
{
    ReplyMessageParser *simpleCmdParser = pClientManager->getClientListModel()->getClient(0)->sendJSCommand(command);
    QString result=simpleCmdParser->getJSEngineResult().toString();
    QByteArray ba = result.toLatin1();
    int retcode=simpleCmdParser->getResultCode();
    qDebug()<<"ret code: "<< retcode;
    strcpy(response,ba.data());
    return retcode;
}

MescApiHandler::~MescApiHandler()
{
    pClientManager->getClientListModel()->getClient(0)->close();
    delete pClientManager;
    qDebug() << "Closed";
}
