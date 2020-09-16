#include <winsock2.h>
#include "server.h"
#define DEFAULT_BUFLEN 1024
#include <QLibrary>
#include <windows.h>
#include <ws2tcpip.h>
#include <string.h>
#include "mescapihandler.h"

Server::Server(char* port)
{
    WSADATA wsaData;
    int iResult;
    printf("%s\n", port);
    strcpy(server_port,port);

    iResult = WSAStartup(MAKEWORD(2,2), &wsaData);
}


int Server::run()
{
    int iResult,mResult;
    SOCKET ListenSocket = INVALID_SOCKET;
    SOCKET ClientSocket = INVALID_SOCKET;

    struct addrinfo *result = NULL;
    struct addrinfo hints;

    int iSendResult;
    char recvbuf[DEFAULT_BUFLEN];
    int recvbuflen = DEFAULT_BUFLEN;
    BOOL bOptVal = FALSE;
    int bOptLen = sizeof (BOOL);



    ZeroMemory(&hints, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;
    hints.ai_flags = AI_PASSIVE;

    char response[1024*512];
    MescApiHandler *m = new MescApiHandler();

    // Resolve the server address and port
    iResult = getaddrinfo(NULL, server_port, &hints, &result);
    if ( iResult != 0 ) {
        printf("getaddrinfo failed with error: %d\n", iResult);
        WSACleanup();
        return 1;
    }


    // Create a SOCKET for connecting to server
    ListenSocket = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if (ListenSocket == INVALID_SOCKET) {
        printf("socket failed with error: %ld\n", WSAGetLastError());
        freeaddrinfo(result);
        WSACleanup();
        return 1;
    }

    // Setup the TCP listening socket
    iResult = bind( ListenSocket, result->ai_addr, (int)result->ai_addrlen);
    if (iResult == SOCKET_ERROR) {
        printf("bind failed with error: %d\n", WSAGetLastError());
        freeaddrinfo(result);
        closesocket(ListenSocket);
        WSACleanup();
        return 1;
    }

    freeaddrinfo(result);

    iResult = setsockopt(ListenSocket, SOL_SOCKET, SO_REUSEADDR, (char *) &bOptVal, bOptLen);
    printf("%i\n", iResult);
    if (iResult == SOCKET_ERROR) {
        printf("setsockopt for SO_KEEPALIVE failed with error: %u\n", WSAGetLastError());
    } else
        printf("Set SO_REUSEADDR: ON\n");

    iResult = listen(ListenSocket, SOMAXCONN);
    printf("Listening\n");
    if (iResult == SOCKET_ERROR) {
        printf("listen failed with error: %d\n", WSAGetLastError());
        closesocket(ListenSocket);
        WSACleanup();
        return 1;
    }

    // Accept a client socket
    ClientSocket = accept(ListenSocket, NULL, NULL);
    if (ClientSocket == INVALID_SOCKET) {
        printf("accept failed with error: %d\n", WSAGetLastError());
        closesocket(ListenSocket);
        WSACleanup();
        return 1;
    }

    // No longer need server socket
    closesocket(ListenSocket);

    // Receive until the peer shuts down the connection
    do {
        memset( recvbuf, '\0', sizeof(char)*DEFAULT_BUFLEN );
        iResult = recv(ClientSocket, recvbuf, recvbuflen, 0);
        if (iResult > 0) {
            printf("Bytes received: %d\n", iResult);
            printf(recvbuf);
            mResult=m->send(recvbuf, response);
            if (mResult!=MESC_NO_ERROR)
            {
                sprintf(response, "{\"MESc Error code\": %d}", mResult);
            }
            // Echo the buffer back to the sender
            iSendResult = send( ClientSocket, response, (int)(strlen(response)), 0 );
            if (iSendResult == SOCKET_ERROR) {
                printf("send failed with error: %d\n", WSAGetLastError());
                closesocket(ClientSocket);
                WSACleanup();
                return 1;
            }
            printf("Bytes sent: %d\n", iSendResult);
        }
        else if (iResult == 0)
            printf("Connection closing...\n");
        else  {
            printf("recv failed with error: %d\n", WSAGetLastError());
            closesocket(ClientSocket);
            WSACleanup();
            return 1;
        }

    } while (iResult > 0);

    // shutdown the connection since we're done
    iResult = shutdown(ClientSocket, SD_SEND);
    if (iResult == SOCKET_ERROR) {
        printf("shutdown failed with error: %d\n", WSAGetLastError());
        closesocket(ClientSocket);
        WSACleanup();
        return 1;
    }
    delete m;
    return 0;
}


Server::~Server()
{
    WSACleanup();
}
