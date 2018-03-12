QT += core websockets

QT -= gui



CONFIG += c++11



TARGET = MEScApiServer

CONFIG += console

CONFIG -= app_bundle



TEMPLATE = app



SOURCES += main.cpp \
    mescapihandler.cpp \
    server.cpp



INCLUDEPATH += c:/MEScAPI/Matlab/



win32 {

    LIBS += -LC:/MEScAPI/Matlab/ -lMEScAPI -lws2_32

}

HEADERS += \
    mescapihandler.h \
    server.h
