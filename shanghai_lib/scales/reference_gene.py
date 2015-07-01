from shanghai_lib.loci_objects import transcript
from shanghai_lib.exceptions import InvalidTranscript

class gene:
    
    def __init__(self, tr:transcript, gid=None):
        
        self.chrom, self.start, self.end, self.strand = tr.chrom, tr.start, tr.end, tr.strand
        self.id = gid
        self.transcripts = dict()
        self.transcripts[tr.id]=tr
        
    def add(self, tr:transcript):
        self.start=min(self.start, tr.start)
        self.end = max(self.end, tr.end)
        self.transcripts[tr.id]=tr
        assert self.strand == tr.strand
        
    def __getitem__(self, tid:str) -> transcript:
        return self.transcripts[tid]
    
    def finalize(self, exclude_utr=False):
        self.exception_message=''
        to_remove=set()
        for tid in self.transcripts:
            try:
                self.transcripts[tid].finalize()
                if exclude_utr is True:
                    self.transcripts[tid].remove_utrs()
            except InvalidTranscript as err:
                self.exception_message += "{0}\n".format(err)
                to_remove.add(tid)
            except Exception as err:
                print(err)
                raise
        for k in to_remove:
            del self.transcripts[k]
    
    def remove(self, tid:str):
        del self.transcripts[tid]
        if len(self.transcripts)==0:
            self.end=None
            self.start=None
            self.chrom=None
        self.start = min(self.transcripts[tid].start for tid in self.transcripts)
        self.end = max(self.transcripts[tid].end for tid in self.transcripts)
    
    def __str__(self):
        return " ".join(self.transcripts.keys())
    
    def __iter__(self) -> transcript:
        '''Iterate over the transcripts attached to the gene.'''
        return iter(self.transcripts.values())
    
    def __len__(self) -> int:
        return len(self.transcripts)
        