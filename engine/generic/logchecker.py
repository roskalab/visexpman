import logging,unittest,os,time,numpy,sys
from visexpman.engine.generic import utils,fileop

def logline2timestamp(line):
    return utils.datestring2timestamp(line.split('\t')[0].split(',')[0],format='%Y-%m-%d %H:%M:%S')

class LogChecker(object):
    '''
    checks logfiles in a specific folder, gathers most recent errors and sends a summary in email
    '''
    def __init__(self,logfile_folder,logfile,to='zoltan.raics@fmi.ch'):
        self.logfile=logfile
        self.nlines_before_error=2
        if os.path.exists(self.logfile):
            content=fileop.read_text_file(self.logfile)
            done_timestamps=[self._line2timestamp(l) for l in content.split('\n') if 'Done' in l]
            if len(done_timestamps)==0:
                self.t0=0
            else:
                self.t0=max(done_timestamps)
        else:
            self.t0=0
        logging.basicConfig(filename= self.logfile,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.INFO)
        logging.info('Log checker started')
        self.logfiles=[f for f in fileop.find_files_and_folders(logfile_folder)[1] if os.path.splitext(f)[1]=='.txt']
        self.error_report='Errors since {0}\n'.format(utils.timestamp2ymdhm(self.t0))
        for f in self.logfiles:
            self.error_report+=self.checkfile(f)
        utils.sendmail(to, 'errors, {0}'.format(logfile_folder), self.error_report)
        logging.error(self.error_report)
        logging.info('Done')
        
    def _line2timestamp(self,line):
        return logline2timestamp(line)
        
    def checkfile(self,filename):
        if os.path.getmtime(filename)<self.t0:#File has not been modified since last run
            return ''
        lines=fileop.read_text_file(filename).split('\n')
        #Find entry indexes
        entry_lines=[]
        for i in range(len(lines)):
            try:
                self._line2timestamp(lines[i])
                entry_lines.append(i)
            except:
                pass
        error_indexes = numpy.array([i for i in entry_lines if 'error' in lines[i].lower()])
        lines2report=[]
        for ei in error_indexes:
            start=ei-self.nlines_before_error-1
            if start<0:
                start=0
            endindex=entry_lines.index(ei)+1+self.nlines_before_error
            if endindex>len(entry_lines)-1:
                endindex=len(entry_lines)-1
            end=entry_lines[endindex]
            if self._line2timestamp(lines[ei])>self.t0:
                lines2report.extend(range(start,end))
        lines2report=set(lines2report)
        if len(lines2report)==0:
            return ''
        error_report=30*'='+'\nErrors in {0}\n'.format(filename)+30*'='+'\n'
        for i in lines2report:
                error_report+=lines[i]
        return error_report
        
class Usage(object):
    def __init__(self,folder,timerange=None):
        self.folder=folder
        if timerange is None:
            self.t1=time.time()
            self.t0=self.t1-86400
        else:
            self.t0=timerange[0]
            self.t1=timerange[1]
        self.tstep=3600*3
        self.tbins=numpy.arange(self.t0,self.t1,self.tstep)
        self.tbins=numpy.append(self.tbins,self.t1)
        
    def aggregate_timestamps(self):
        self.logfiles=[os.path.join(self.folder,f) for f in os.listdir(self.folder) if os.path.splitext(f)[1]=='.txt']
        timestamps={}
        for f in self.logfiles:
            if os.path.getmtime(f)<self.t0: continue
            print f
            lines=fileop.read_text_file(f).split('\n')
            timestamps[f]=[]
            for l in lines:
                try:
                    timestamps[f].append(logline2timestamp(l))
                except:
                    pass
        self.timestamps=timestamps
        return timestamps
        
    def plot(self):
        ts=numpy.concatenate(map(numpy.array,self.timestamps.values()))
        self.hist,b=numpy.histogram(ts,self.tbins)
        from pylab import plot,savefig,show
        x=(self.tbins[:-1]-self.tbins[-1])/3600.
        plot(x,self.hist);show()#TODO: date time on x axis
        
    
class TestLogChecker(unittest.TestCase):
    @unittest.skip('') 
    def test_01(self):
        lc=LogChecker('/tmp/logtest','/tmp/log_checker.txt')
        print lc.error_report
        lc.t0=0
        print lc.checkfile('/tmp/logtest/log_behav_2016-12-06_14-47-52.txt')
        
    def test_02_usage_stat(self):
        now=time.time()
        u=Usage('/tmp/log',[now-3*86400,now])
        u.aggregate_timestamps()
        u.plot()
    
if __name__ == "__main__":
    if len(sys.argv)==1:
        unittest.main()
    else:
        lc=LogChecker(*sys.argv[1:])
