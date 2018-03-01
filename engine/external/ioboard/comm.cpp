#include "comm.h"
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#if (PLATFORM==PC)
  #include <iostream>
  using namespace std;
#endif

#if (PLATFORM==ARDUINO_UNO)
  #include "Arduino.h"
  #include "config.h"
#endif


Comm::Comm(void)
{
    memset(buffer,0,COMM_BUFFER_SIZE);
}

int Comm::parse(void)
{   
    int eoc;//end of command index
    int sop[MAX_PARAMS]; //start of parameter indexes
    int i,j,param_counter,sp,ep,n;
    char* buffer_chunk;
    bool eoc_found=false;
    bool parameter_error=false;
    /*
    1. Find end of command character, save this index
    2. go through buffer until end of command and save index of parameter delimiter character.
    3. Iterate through each delimiter index and extract float value from buffer chunk
    4. extract command
    5. Remove parsed command from buffer
    */
    memset(command,0,sizeof(command));
    nparams=0;
    for(i=0;i<COMM_BUFFER_SIZE;i++)
    {
//        cout<<i<<" "<< buffer[i]<<endl;
        if (buffer[i]==ENDOFCOMMAND)
        {
            eoc=i;
            eoc_found=true;
            break;
        }
    }
//    cout<<endl<<"eoc found "<<eoc_found<<" "<< i<<endl;
    if (!eoc_found)
    {   
        return NO_COMMAND_TERMINATOR;
    }
    param_counter=0;
    for(i=0;i<eoc;i++)
    {
        if (buffer[i]==STARTOFPARAM)
        {
            sop[param_counter]=i;
            param_counter++;
        }
    }
    for(i=0;i<param_counter;i++)
    {
        sp=sop[i]+1;
        if (i==param_counter-1)
        {
            ep=eoc;
        }
        else
        {
            ep=sop[i+1];
        }
        n=ep-sp;
        
        for(j=0;j<n;j++)
        {
            if (isalpha(buffer[sp+j]))
            {
                parameter_error=true;
            }
            parameter_buffer[j]=buffer[sp+j];
        }
        if (parameter_error)
        {
            flush_command(eoc);
            return WRONG_PARAMETER;
        }
        parameter_buffer[n]=0;
        par[i]=atof(parameter_buffer);
        #if DEBUG_PARSE
            cout<<sp<<" "<<ep<<" "<<n<<" "<<parameter_buffer<<endl;
        #endif
    }
    nparams=param_counter;
    n=(param_counter>0) ? sop[0] : (eoc-1);
    memcpy(command,buffer,n);
    //Remove parsed command from buffer
    flush_command(eoc);
    if (n<COMMAND_NAME_SIZE)
        command[n]=0;
    #if DEBUG_PARSE
        cout<<endl<<"--debug--"<<endl<<command<<" "<< nparams<<endl<<buffer<<endl;
        for(i=0;i<nparams;i++)
        {
            cout <<par[i]<<endl;
        }
    #endif
    return NO_ERROR;
}

void Comm::flush_command(int index)
{
    int i;
    for (i=0;i<COMM_BUFFER_SIZE-(index+2);i++)
    {
        buffer[i]=buffer[i+index+2];
    }
    buffer[i+index+2]=0;

}

void Comm::put(char* c)
{
    strcat(buffer, c);
}

void Comm::debug_pulse(void)
{
#if (PLATFORM==ARDUINO_UNO)
  digitalWrite(DEBUGPIN, HIGH);
  delayMicroseconds(DEBUG_PULSE_DURATION_US);
  digitalWrite(DEBUGPIN, LOW);
#endif
}

