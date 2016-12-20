#include "comm.h"
#include <stdlib.h>
#include <string.h>
#include <iostream>
using namespace std;

Comm::Comm(void)
{
    strcpy(buffer, "");
}

void Comm::parse(void)
{   
    int eoc;//end of command index
    int sop[MAX_PARAMS]; //start of parameter indexes
    int i,j,param_counter,sp,ep,n;
    char* buffer_chunk;
    /*
    1. Find end of command character, save this index
    2. go through buffer until end of command and save index of parameter delimiter character.
    3. Iterate through each delimiter index and extract float value from buffer chunk
    4. extract command
    5. Remove parsed command from buffer
    */
    for(i=0;i<COMM_BUFFER_SIZE;i++)
    {
        if (buffer[i]==ENDOFCOMMAND)
        {
            eoc=i;
            break;
        }
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
            parameter_buffer[j]=buffer[sp+j];
        }
        parameter_buffer[n]=0;
        cout<<sp<<" "<<ep<<" "<<n<<" "<<parameter_buffer<<endl;
    }
    memcpy(command,buffer,eoc);
    
    cout<<endl<<"--debug--"<<endl<<buffer<<" "<<eoc<<" "<<command<<endl;
}

void Comm::put(char* c)
{
    strcat(buffer, c);

}
