import logging,unittest,os,time,numpy,sys
from visexpman.engine.generic import utils,fileop,stringop
ct=1


def logline2timestamp(line):
    try:
        return utils.datestring2timestamp(line.split('\t')[0].split(',')[0].split('.')[0],format='%Y-%m-%d %H:%M:%S')
    except:
        return 0

class LogChecker(object):
    '''
    checks logfiles in a specific folder, gathers most recent errors and sends a summary in email
    '''
    def __init__(self,logfile_folder,logfile,to='zoltan.raics@fmi.ch', ignore='ignore this', include = ''):
        self.logfile=logfile
        self.nlines_before_error=3
        content=''
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
        includel=include.split('_')
        self.logfiles=[f for f in fileop.find_files_and_folders(logfile_folder)[1] if os.path.splitext(f)[1]=='.txt' and not (f in content) and ignore not in os.path.basename(f) and (stringop.string_in_list(includel, f, any_match=True) or len(include)==0)]
        self.error_report='Errors since {0}\n'.format(utils.timestamp2ymdhm(self.t0))
        msglen=len(self.error_report)
        self.logfiles.sort()
        logging.info('Parse each logfile')
        for f in self.logfiles:
            logging.info(f)
            logging.info((self.logfiles.index(f), len(self.logfiles), f))
            self.error_report+=self.checkfile(f)
        logging.info((msglen, len(self.error_report)))
        if self.t0!=0 and len(self.error_report)>msglen:#Ignore errors at very first run
            utils.sendmail(to, 'errors in {0}'.format(logfile_folder), self.error_report)
            logging.error(self.error_report)
        logging.info('Done')
        
    def _line2timestamp(self,line):
        return logline2timestamp(line)
        
    def checkfile(self,filename):
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
            #if self._line2timestamp(lines[ei])>self.t0:
            lines2report.extend(range(start,end))
        lines2report=set(lines2report)
        if len(lines2report)==0:
            return ''
        error_report=30*'='+'\nErrors in {0}\n'.format(filename)+30*'='+'\n'
        for i in lines2report:
                error_report+=lines[i]
        return error_report
        
class Usage(object):
    def __init__(self,folder,timerange=None, exclude=[]):
        self.folder=folder
        self.exclude=exclude
        if timerange is None:
            self.t1=time.time()
            self.t0=self.t1-86400
        else:
            self.t0=timerange[0]
            self.t1=timerange[1]
        self.tstep=3600
        self.tbins=numpy.arange(self.t0,self.t1,self.tstep)
        self.tbins=numpy.append(self.tbins,self.t1)
        
    def aggregate_timestamps(self):
        self.logfiles=[os.path.join(self.folder,f) for f in os.listdir(self.folder) if os.path.splitext(f)[1]=='.txt']
        filtered_files=[]
        for l in self.logfiles:
            if len([True for kw in self.exclude if kw in l])==0:
                filtered_files.append(l)
        self.logfiles=filtered_files
        timestamps={}
        for f in self.logfiles:
            if os.path.getmtime(f)<self.t0: continue
            print f
            lines=fileop.read_text_file(f).split('\n')
            timestamps[f]=[]
            for l in lines:
                try:
                    ts=logline2timestamp(l)
                    if ts>0:
                        timestamps[f].append(ts)
                except:
                    pass
            pass
        self.timestamps=timestamps
        return timestamps
        
    def plot(self, fn):
        ts=numpy.concatenate(map(numpy.array,self.timestamps.values()))
        self.tbins=[]
        self.hist=[]
        legendtxt=[]
        maxh=[]
        for d in range(int((self.t1-self.t0)/86400)):
            bins=numpy.linspace(self.t0+d*86400,self.t0+(d+1)*86400,24)
            h,b=numpy.histogram(ts,bins)
            maxh.append(h.max())
            self.hist.append(h)
            self.tbins.append(bins)
            legendtxt.append(utils.timestamp2ymd(bins[0]))
        from pylab import plot,savefig,show, gca,legend,subplot,title,tight_layout,ylim,cla,clf,figure
        from matplotlib.dates import DateFormatter
        import datetime,matplotlib
        global ct
        figure(ct)
        ct+=1
        cla()
        clf()
        font = {
                'size'   : 6}
        matplotlib.rc('font', **font)
        gca().xaxis.set_major_formatter(DateFormatter('%H:%M'))
        nplots=len(self.hist)
        for d in range(len(self.hist)):
            subplot(nplots,1,d+1)
            x=[datetime.datetime.fromtimestamp(xi%86400) for xi in self.tbins[d]]
            plot(x[1:],self.hist[d])
            title(legendtxt[d])
            #ylim((0,maxh[d]))
        tight_layout()
        savefig(fn, dpi=300)
        
def aggregate_usage():
    folders=\
        ['/mnt/datafast/log',
            '/data/behavioral',
            '/data/santiago-setup/log',
            '/data/rei-setup/log']
    now=time.time()
    now-=int(now)%86400
    for folder in folders:
        u=Usage(folder,[now-7*86400,now], ['purger', 'backup', 'bu_'])
        u.aggregate_timestamps()
        u.plot(os.path.join('/data/data/user/Zoltan', os.path.basename(os.path.dirname(folder))+'.png'))
    
class TestLogChecker(unittest.TestCase):
    @unittest.skip('') 
    def test_01(self):
        lc=LogChecker('/tmp/logtest','/tmp/log_checker.txt')
        print lc.error_report
        lc.t0=0
        print lc.checkfile('/tmp/logtest/log_behav_2016-12-06_14-47-52.txt')
        
    def test_02_usage_stat(self):
        now=time.time()
        now-=int(now)%86400
        u=Usage('/tmp/log',[now-7*86400,now], ['purger', 'backup', 'bu_'])
        u.aggregate_timestamps()
        u.plot('/tmp/1.png')
    
if __name__ == "__main__":
    if len(sys.argv)==1:
        unittest.main()
    else:
        lc=LogChecker(*sys.argv[1:])
