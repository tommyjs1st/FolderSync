import sys
import os
import time
import datetime
import shutil

from threading import Thread
from difflib import Differ
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

class FolderSync(Thread):

    def __init__(self, configList):
        Thread.__init__(self)
        self.configList = configList

    def run(self):
        global cntDelete, cntUpdate, fileListOld, fileListNew
        global modeVerbose

        dstFolder =''
        srcFolders = []

        # 화면값이 아니라 설정파일에서 읽어온다.(배치모드 실행을 감안해서)
        for fileNo in range(2):
            
            if modeVerbose and fileNo == 0: progressbar.start(50)
            elif modeVerbose and fileNo == 1: progressbar2.start(50)

            try:
                f = open(configList[fileNo], 'r')
                lines = f.readlines()
                lineCnt = 0
                srcFolders = []
                for line in lines:
                    if lineCnt == 1:
                        dstFolder = self.deleteEscChar(line)
                    elif lineCnt > 2:
                        srcFolders.append(self.deleteEscChar(line))
                    lineCnt += 1
                f.close()
        
                if not os.path.exists(os.path.dirname(dstFolder)):
                    os.mkdir(os.path.dirname(dstFolder))
        
                for srcFolder in srcFolders:
                    tarFolder = os.path.basename(srcFolder)
                    tarFolder = os.path.join(dstFolder, os.path.basename(srcFolder))
                    #fileLog(srcFolder + " >>>> " + tarFolder)

                    #파일 비교 시작
                    self.folderSync(srcFolder, tarFolder)

            except Exception as e:
                print('file open error!', e)
            
            if modeVerbose and fileNo == 0: progressbar.stop()
            elif modeVerbose and fileNo == 1: progressbar2.stop()

        mesg = ''
        if (cntDelete + cntUpdate) > 0:
            mesg = str(cntDelete) + '개 삭제, ' + str(cntUpdate) + '개 변경/추가'          
        else:
            mesg = '변경사항 없음'
        self.fileLog(mesg)

        if modeVerbose:
            listboxlog.activate(0)
            btnstart['state'] = 'normal'
            messagebox.showinfo(title="작업완료 안내", message=mesg)
            
    def saveList(self, folder, listFilename, jobType):
        file = open(listFilename, 'w')

        for root, dirs, files in os.walk(folder):
            if (jobType == 'D'):
                for dir in dirs:
                    full_dir = os.path.join(root, dir)
                    full_dir = full_dir.replace(folder, '')
                    file.write(full_dir + '\n')
                    #print(full_dir)
            else:
                for fname in files:
                    full_fname = os.path.join(root, fname)
                    mtime = os.path.getmtime(full_fname)
                    fsize = os.path.getsize(full_fname)
                    full_fname = full_fname.replace(folder, '')
                    try:
                        file.write(full_fname + '|' + str(mtime) + '|' + str(fsize) + '\n')
                    except Exception as e:
                        continue
        
        file.close()


    def readList(self, listFilename):
        file = open(listFilename, 'r')

        lines = file.readlines()
        for line in lines:
            print(deleteEscChar(line))
        file.close()
        print("-----------------------------")

    def deleteEscChar(self, inStr):
        outStr = ''
        for c in inStr:
            if ord(c) > 31:
                outStr += c
        return outStr

    def fileLog(self, mesg):
        global modeVerbose, logFile
        f = open(logFile, 'a')
        f.write('[%s] %s\n' % (str(datetime.datetime.now()), mesg))
        if modeVerbose:
            listboxlog.insert(0, mesg)

    def folderSync(self, srcFolder, dstFolder):

        global cntDelete, cntUpdate, fileListOld, fileListNew

        try:
            # 00. 대상폴더 생성 및 위치로 이동
            if not os.path.exists(os.path.dirname(fileListOld)):
                os.mkdir(os.path.dirname(fileListOld))
   
            if not os.path.exists(dstFolder):
                #print(dstFolder + " not found.")
                os.mkdir(dstFolder)
            os.chdir(dstFolder)
        except Exception as e:
            print('file read error!', e)
            self.fileLog(e)
            return

        #01.현재 폴더구조를 파일로 저장
        self.saveList(srcFolder, fileListNew, 'D')
        self.saveList(dstFolder, fileListOld, 'D')
    
        #02. 폴더 구조 동기화
        with open(fileListOld) as f1, open(fileListNew) as f2:
            differ = Differ()
            for line in differ.compare(f1.readlines(), f2.readlines()):
                line = self.deleteEscChar(line)
                #print(line)
                if line.startswith("-"):    #백업폴더 삭제
                    delFolder = dstFolder + line[2:]
                    shutil.rmtree(delFolder)
                    self.fileLog('\tD ' + delFolder)
                
                elif line.startswith("+"):    #새 폴더 생성
                    #print(dstFolder + line[2:])
                    newFolder = dstFolder + line[2:]
                    os.mkdir(newFolder)
                    self.fileLog('\tU ' + newFolder)

        #print("folder sync ok")
        #11.현재 파일 상태를 파일로 저장
        self.saveList(srcFolder, fileListNew, 'F')
        self.saveList(dstFolder, fileListOld, 'F')
            
        #12.파일상태 비교(현재 파일과 이전 파일 비교)
        #13.변경된 파일을 복사 및 삭제된 파일을 백업폴더에서 삭제
        with open(fileListOld) as f1, open(fileListNew) as f2:
            differ = Differ()
            for line in differ.compare(f1.readlines(), f2.readlines()):
                #print(line, end="")
                if line.startswith("-"):    #백업파일 삭제
                    #print(line)
                    len = line[2:].find("|") + 2
                    dstFile = os.path.join(dstFolder, line[3:len])                
                    self.fileLog('\tD ' + dstFile)
                    cntDelete += 1
                    os.remove(dstFile)
                    #shutil.rmtree(dstFile)
                elif line.startswith("+"):    #새 파일 복사
                    len = line[2:].find("|") + 2
                    dstFile = line[3:len]
                    dstFile = os.path.join(dstFolder, dstFile)
                    #srcFile = os.path.join(srcFolder, dstFile)
                    srcFile = srcFolder + '\\' + line[2:len]
                    shutil.copy2(srcFile, dstFile)
                    self.fileLog('\tU ' + srcFile )
                    cntUpdate += 1
                #elif line.startswith("?"):
                #    fileLog(line)



# 백업대상/저장위치를 파일에 저장
def saveConfig(tgt):
    global listboxfr, listboxto, listboxfr2, listboxto2
    global configList
    if tgt==0:
        dstDirList = listboxto.get(0,'end')
        srcDirList = listboxfr.get(0,'end')
    else:
        dstDirList = listboxto2.get(0,'end')
        srcDirList = listboxfr2.get(0,'end')
    
    f = open(configList[tgt], 'w')
    f.write('[저장위치]\n')
    if len(dstDirList) > 0:
        f.write(dstDirList[0]+'\n')
    else:
        f.write('\n')   
    f.write('[백업대상]\n')
    if len(srcDirList) > 0:
        for list in srcDirList:
            f.write(list + '\n')
    f.close()

# 백업대상/저장위치를 파일에서 읽어서 화면에 표시    
def readConfig(configfile, listboxfr, listboxto):
    dstDirList = listboxto.get(0,'end')
    srcDirList = listboxfr.get(0,'end')

    try:
        f = open(configfile, 'r')
        lines = f.readlines()
        lineCnt = 0
        for line in lines:
            if lineCnt == 1:
                listboxto.insert(0, deleteEscChar(line))
            elif lineCnt > 2:
                listboxfr.insert(999, deleteEscChar(line))
            lineCnt += 1
        f.close()
    except Exception as e:
        print('file read error!', e)
        

def deleteEscChar(inStr):
    outStr = ''
    for c in inStr:
        if ord(c) > 31:
            outStr += c
    return outStr


def pgmStart_click():
    
    folderSync = FolderSync(configList)
    folderSync.start() #동기화 작업시작
    
    if modeVerbose:
        btnstart['state'] = 'disabled'
        listboxlog.delete(0,'end')
    else:
        folderSync.join()
    
def srcFolderSelect_click():
    srcFolderSelect(0, listboxfr)
def srcFolderSelect_click2():
    srcFolderSelect(1, listboxfr2)
def srcFolderSelectDel_click():
    srcFolderSelectDel(0, listboxfr)
def srcFolderSelectDel_click2():
    srcFolderSelectDel(1, listboxfr2)
def dstFolderSelect_click():
    dstFolderSelect(0, listboxto)
def dstFolderSelect_click2():
    dstFolderSelect(1, listboxto2)
    
    
def srcFolderSelect(tgt, listbox):    #백업대상 선택
    win.srcDirName = filedialog.askdirectory()
    if (win.srcDirName == ''): return
    
    # 이미 백업대상에 없는 경우에만 추가/저장
    bInList = False
    srcDirList = listbox.get(0,'end')
    if win.srcDirName not in srcDirList:
        listbox.insert(999, win.srcDirName)
        saveConfig(tgt)
        
def srcFolderSelectDel(tgt, listbox): #선택된 백업대상 삭제
    itms = listbox.curselection()
    for index in itms[::-1]:
        listbox.delete(index)
    saveConfig(tgt)
        
def dstFolderSelect(tgt, listbox):    #저장폴더 선택
    win.dstDirName = filedialog.askdirectory()
    if (win.dstDirName == ''): return
    
    listbox.delete(0, END)
    listbox.insert(0, win.dstDirName)
    saveConfig(tgt)

#
# 프로그램 시작(GUI)
#
cntDelete = 0
cntUpdate = 0
modeVerbose = True

workingDir = os.getcwd()

fileListOld = os.path.join(workingDir, 'listOld.txt')            #임시 작업파일
fileListNew = os.path.join(workingDir, 'listNew.txt')            #임시 작업파일
logFile = os.path.join(workingDir, 'folderSync.log')
configFiles = ['folderSync1.ini', 'folderSync2.ini']

configList = []
for configfile in configFiles:
    configList.append(os.path.join(workingDir, configfile))


#화면모드 실행 여부
args = sys.argv[1:]
if '-c' in args or '-C' in args:
    modeVerbose = False
          
    pgmStart_click()
    sys.exit()


win=Tk()
win.title("폴더 동기화 프로그램")
win.geometry("720x480+100+100")
win.resizable(False, False)

btnstart = Button(win, text = '작업시작', width=100, command = pgmStart_click)
btnstart.pack(side= 'top', padx=5, pady = 5)

#버튼
framebtn=Frame(win)
btnfr = Button(framebtn, text = '백업대상', width=10, command = srcFolderSelect_click)
btnfrdel = Button(framebtn, text = '선택파일 삭제', width=10, command = srcFolderSelectDel_click)
btnto = Button(framebtn, text = '저장위치', width=10, command = dstFolderSelect_click)
btnfr.pack(side= 'left', anchor='w', padx=5, pady = 5)
btnfrdel.pack(side= 'left', anchor='w', padx=5, pady = 5)
btnto.pack(side= 'right', anchor='ne', padx=5, pady = 5)

#진행표시
progressbar=ttk.Progressbar(framebtn, length=450, maximum=100, mode="indeterminate")
progressbar.pack(side='left')


#리스트박스
framelist1=Frame(win)
framelog=Frame(win)
framefr=Frame(framelist1)
frameto=Frame(framelist1)
scrollbarlog = Scrollbar(framelog)
scrollbarfr = Scrollbar(framefr)
scrollbarto = Scrollbar(frameto)
scrollbarlog.pack(side='right', fill='y')
scrollbarfr.pack(side='right', fill='y')
scrollbarto.pack(side='right', fill='y')
listboxlog = Listbox(framelog, selectmode='extended',width=100, height=10, yscrollcommand=scrollbarlog.set)
listboxfr = Listbox(framefr, selectmode='extended',width=48, height=7, yscrollcommand=scrollbarfr.set)
listboxto = Listbox(frameto, selectmode='extended',width=48, height=7, yscrollcommand=scrollbarto.set)
listboxfr.pack(side='left')
listboxto.pack(side='right')
listboxlog.pack(side='bottom')

scrollbarlog["command"]=listboxlog.yview
scrollbarfr["command"]=listboxfr.yview
scrollbarto["command"]=listboxto.yview

framebtn.pack(side='top')
framelog.pack(side='bottom')
framefr.pack(side='left', anchor='nw')
frameto.pack(side='right', anchor='ne')
framelist1.pack()

#버튼
framebtn2=Frame(win)
btnfr2 = Button(framebtn2, text = '백업대상', width=10, command = srcFolderSelect_click2)
btnfrdel2 = Button(framebtn2, text = '선택파일 삭제', width=10, command = srcFolderSelectDel_click2)
btnto2 = Button(framebtn2, text = '저장위치', width=10, command = dstFolderSelect_click2)
btnfr2.pack(side= 'left', anchor='w', padx=5, pady = 5)
btnfrdel2.pack(side= 'left', anchor='w', padx=5, pady = 5)
btnto2.pack(side= 'right', anchor='ne', padx=5, pady = 5)

#진행표시
progressbar2=ttk.Progressbar(framebtn2, length=450, maximum=100, mode="indeterminate")
progressbar2.pack(side='left')
framebtn2.pack()

framelist2=Frame(win)
framefr2=Frame(framelist2)
frameto2=Frame(framelist2)
scrollbarfr2 = Scrollbar(framefr2)
scrollbarto2 = Scrollbar(frameto2)
scrollbarfr2.pack(side='right', fill='y')
scrollbarto2.pack(side='right', fill='y')
listboxfr2 = Listbox(framefr2, selectmode='extended',width=48, height=7, yscrollcommand=scrollbarfr2.set)
listboxto2 = Listbox(frameto2, selectmode='extended',width=48, height=7, yscrollcommand=scrollbarto2.set)
listboxfr2.pack(side='left')
listboxto2.pack(side='right')
framefr2.pack(side='left')
frameto2.pack(side='right')
framelist2.pack()

readConfig(configFiles[0], listboxfr, listboxto)
readConfig(configFiles[1], listboxfr2, listboxto2)

win.mainloop()


