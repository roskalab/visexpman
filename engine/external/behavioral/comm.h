/*
Communication class for parsing commands which come in the following format:
    command,val1,val2\r\n
    command\r\n
    command,val1,val2
    val1,val2 can be only float
*/
#define COMM_BUFFER_SIZE 256
#define COMMAND_SIZE 32
#define COMMAND_NAME_SIZE 16
#define MAX_PARAMS 8
#define STARTOFPARAM ','
#define ENDOFCOMMAND '\r'

class Comm {
    public:
        Comm(void);
        void parse(void);
        void put(char* c);
        char buffer[COMM_BUFFER_SIZE];
        float par[MAX_PARAMS];
        int nparams;
        char command[COMMAND_NAME_SIZE];
    private:
        char parameter_buffer[COMMAND_NAME_SIZE];

        


};


