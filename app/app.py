#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2020 Quoc-Nam Dessoulles
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Main application class."""

__author__ = "Quoc-Nam Dessoulles"
__email__ = "cokie.forever@gmail.com"
__license__ = "MIT"

import os
import re
import time
import tkinter as tk
import tkinter.filedialog
import tkinter.messagebox
from contextlib import contextmanager
from queue import Queue, Empty
from threading import Thread
from tkinter import ttk

from app.util import optionMenu, button, label, scrolledText, checkButton, entry, findAll

SEARCH_TAG = "Search"
CURRENT_SEARCH_TAG = "CurrentSearch"
FILTER_TAG = "Filter"


class Expression:
    def __init__(self, sText, oLogLevel):
        self.sText = sText
        self.oLogLevel = oLogLevel
        self.sStartIdx = None
        self.sEndIdx = None
        self.bDisplay = True


class LogLevel:
    def __init__(self, sName, oRegex, sColor):
        self.sName = sName
        self.oRegex = oRegex
        self.sColor = sColor
        self.bDisplay = True

    @property
    def sTag(self):
        return "LogLevel:" + self.sName

    def matches(self, sLogLine):
        return self.oRegex.search(sLogLine) is not None


class Pattern:
    def __init__(self, sPattern, bRegex):
        self.oRegex = None
        self.bRegex = bRegex
        self.sPattern = sPattern
        self.iLen = len(sPattern)

    def matches(self, sText):
        return not self.sPattern or self.getFirstMatch(sText) is not None

    def getFirstMatch(self, sText):
        return next(self.getAllMatches(sText), None)

    def getAllMatches(self, sText):
        if not self.sPattern:
            return
        if self.bRegex:
            if self.oRegex is None:
                try:
                    self.oRegex = re.compile(self.sPattern)
                except Exception:
                    return
            for m in self.oRegex.finditer(sText):
                yield m.start(), m.end()
        else:
            for i in findAll(sText.lower(), self.sPattern.lower()):
                yield i, i + self.iLen


class Application(ttk.Frame):
    def __init__(self, oMaster=None):
        super().__init__(oMaster)
        self.oMaster = oMaster
        self.oSourceOptionMenu = None
        self.oLogTextArea = None
        self.oHorizontalScrollbar = None
        self.lExpressions = []
        self.oSearchRegexVar = None
        self.oSearchEntry = None
        self.lCurrentSearchResult = None
        self.oFilterRegexVar = None
        self.oFilterEntryVar = None
        self.bWatchFile = False
        self.oFileWatchThread = None
        self.oQueue = Queue()
        self.bProcessQueue = True
        self.oPauseResumeButton = None

        self.lRecentSourceFiles = []
        self.lLogLevels = [
            LogLevel("Error", re.compile(r"^.*\sERROR\s"), "red"),
            LogLevel("Warning", re.compile(r"^.*\sWARN\s"), "orange"),
            LogLevel("Info", re.compile(r"^.*\sINFO\s"), "blue"),
            LogLevel("Debug", re.compile(r"^.*\sDEBUG\s"), "black")
        ]
        self.oLogLineRegex = re.compile(r"^\d{4}-\d{2}-\d{2}")

        self.oMaster.protocol("WM_DELETE_WINDOW", lambda *oArgs: self.onClose())
        self.winfo_toplevel().title("Log Reader")
        self.oMaster.bind("<F3>", lambda _: self.goToNextSearchResult(bBackwards=False))
        self.oMaster.bind("<Shift-F3>", lambda _: self.goToNextSearchResult(bBackwards=True))
        self.oMaster.bind("<Control-f>", lambda _: self.onControlF())
        self.oMaster.bind("<Control-o>", lambda _: self.onChooseSourceButtonClicked())

        self.pack(fill=tk.BOTH, expand=True)
        self.createWidgets()
        self.startQueueProcessing()

    @property
    def oFilterPattern(self):
        return Pattern(self.oFilterEntryVar.get(), self.oFilterRegexVar.get())

    @property
    def oSearchPattern(self):
        return Pattern(self.oSearchEntry.oStringVar.get(), self.oSearchRegexVar.get())

    def createWidgets(self):
        oSourceArea = ttk.Frame(self, relief=tk.RAISED, borderwidth=1)
        oSourceArea.grid(row=0, column=0, columnspan=2, sticky=tk.N + tk.E + tk.W + tk.S, ipady=5)

        label(oSourceArea, "Source: ").pack(side=tk.LEFT, padx=5)
        self.oSourceOptionMenu = optionMenu(oSourceArea, self.lRecentSourceFiles,
                                            xCallback=lambda s: self.openNewSourceFile(s))
        self.oSourceOptionMenu.pack(side=tk.LEFT, fill=tk.X, expand=True)
        button(oSourceArea, "Choose...", xCallback=lambda: self.onChooseSourceButtonClicked()) \
            .pack(side=tk.LEFT, padx=5)

        oFilterArea = ttk.Frame(self, relief=tk.RAISED, borderwidth=1)
        oFilterArea.grid(row=1, column=0, columnspan=2, sticky=tk.N + tk.E + tk.W + tk.S, ipady=5)

        label(oFilterArea, "Log levels: ").pack(side=tk.LEFT, padx=5)
        for oLogLevel in self.lLogLevels:
            checkButton(oFilterArea, oLogLevel.sName, bChecked=oLogLevel.bDisplay,
                        xCallback=lambda b, o=oLogLevel: self.setLogLevelDisplay(o, b)) \
                .pack(side=tk.LEFT, padx=5)
        oFilterRegexButton = checkButton(oFilterArea, "Regex", bChecked=True,
                                         xCallback=lambda _: self.updateLogWidget())
        self.oFilterRegexVar = oFilterRegexButton.oBoolVar
        oFilterRegexButton.pack(side=tk.RIGHT, padx=5)
        oFilterEntry = entry(oFilterArea, iWidth=50, xCallback=lambda _: self.updateLogWidget())
        self.oFilterEntryVar = oFilterEntry.oStringVar
        oFilterEntry.pack(side=tk.RIGHT, padx=5)
        label(oFilterArea, "Filter: ").pack(side=tk.RIGHT, padx=5)

        oSearchArea = ttk.Frame(self, relief=tk.RAISED, borderwidth=1)
        oSearchArea.grid(row=2, column=0, columnspan=2, sticky=tk.N + tk.E + tk.W + tk.S, ipady=5)

        checkButton(oSearchArea, "Wrap lines", bChecked=False, xCallback=lambda b: self.setWrapLines(b)) \
            .pack(side=tk.LEFT, padx=5)
        oSearchRegexButton = checkButton(oSearchArea, "Regex", bChecked=True,
                                         xCallback=lambda _: self.onSearchQueryUpdated())
        self.oSearchRegexVar = oSearchRegexButton.oBoolVar
        oSearchRegexButton.pack(side=tk.RIGHT, padx=5)
        self.oSearchEntry = entry(oSearchArea, iWidth=50, xCallback=lambda _: self.onSearchQueryUpdated())
        self.oSearchEntry.pack(side=tk.RIGHT, padx=5)
        label(oSearchArea, "Search: ").pack(side=tk.RIGHT, padx=5)

        oLeftButtonsArea = ttk.Frame(self, relief=tk.RAISED, borderwidth=1)
        oLeftButtonsArea.grid(row=3, column=0, sticky=tk.N + tk.S + tk.E + tk.W, ipadx=5)
        tk.Grid.rowconfigure(self, 3, weight=1)

        self.oPauseResumeButton = button(oLeftButtonsArea, "Pause", xCallback=lambda: self.onPauseResumeButtonClicked())
        self.oPauseResumeButton.pack(side=tk.TOP, pady=(5, 0))
        button(oLeftButtonsArea, "Clear", xCallback=lambda: self.clearLog()).pack(side=tk.TOP)
        button(oLeftButtonsArea, "Reload", xCallback=lambda: self.startFileWatch(self.lRecentSourceFiles[0])) \
            .pack(side=tk.TOP)
        button(oLeftButtonsArea, "Go to bottom", xCallback=lambda: self.scrollToBottom()).pack(side=tk.TOP)

        oLogArea = ttk.Frame(self)
        oLogArea.grid(row=3, column=1, sticky=tk.N + tk.E + tk.W + tk.S)
        tk.Grid.columnconfigure(self, 1, weight=1)

        self.oLogTextArea = scrolledText(oLogArea)
        for oLogLevel in self.lLogLevels:
            self.oLogTextArea.tag_config(oLogLevel.sTag, foreground=oLogLevel.sColor)
        self.oLogTextArea.config(state=tk.DISABLED)
        self.oLogTextArea.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.oHorizontalScrollbar = tk.Scrollbar(oLogArea, orient=tk.HORIZONTAL)
        self.oHorizontalScrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.setWrapLines(False)

    def setWrapLines(self, bWrapLines):
        if bWrapLines:
            self.oLogTextArea.config(wrap=tk.WORD, xscrollcommand=None)
            self.oHorizontalScrollbar.config(command=None)
        else:
            self.oLogTextArea.config(wrap=tk.NONE, xscrollcommand=self.oHorizontalScrollbar.set)
            self.oHorizontalScrollbar.config(command=self.oLogTextArea.xview)

    def onClose(self):
        self.stopFileWatch()
        self.oMaster.destroy()

    def onControlF(self):
        self.oSearchEntry.focus_set()
        self.oSearchEntry.select_range(0, tk.END)
        self.oSearchEntry.icursor(tk.END)

    def onChooseSourceButtonClicked(self):
        sNewSourceFilePath = tk.filedialog.askopenfilename()
        if sNewSourceFilePath:
            self.openNewSourceFile(sNewSourceFilePath)

    def onPauseResumeButtonClicked(self):
        self.bProcessQueue = not self.bProcessQueue
        self.oPauseResumeButton.config(text="Pause" if self.bProcessQueue else "Resume")

    def onSearchQueryUpdated(self):
        self.updateHighlighting()
        self.lCurrentSearchResult = None
        self.goToNextSearchResult()

    def goToNextSearchResult(self, bBackwards=False):
        if self.lCurrentSearchResult is None:
            sIndex = self.oLogTextArea.index("@0,%d" % self.oLogTextArea.winfo_height()) if bBackwards \
                else self.oLogTextArea.index("@0,0")
            lSearchPos = tuple(map(int, sIndex.split(".")))
        else:
            lSearchPos = self.lCurrentSearchResult[0 if bBackwards else 1]

        lBestStartPos, lBestEndPos = None, None
        oIter = iter(tuple(map(int, oIdx.string.split("."))) for oIdx in self.oLogTextArea.tag_ranges(SEARCH_TAG))
        for lStartPos, lEndPos in zip(*[oIter] * 2):
            if lBestStartPos is None:
                lBestStartPos, lBestEndPos = lStartPos, lEndPos
            elif bBackwards:
                if lBestStartPos < lStartPos < lSearchPos or lStartPos < lSearchPos <= lBestStartPos \
                        or lSearchPos <= lBestStartPos < lStartPos:
                    lBestStartPos, lBestEndPos = lStartPos, lEndPos
            else:
                if lSearchPos <= lStartPos < lBestStartPos or lBestStartPos < lSearchPos <= lStartPos \
                        or lStartPos < lBestStartPos < lSearchPos:
                    lBestStartPos, lBestEndPos = lStartPos, lEndPos

        self.oLogTextArea.tag_delete(CURRENT_SEARCH_TAG)
        if lBestStartPos is not None:
            self.lCurrentSearchResult = lBestStartPos, lBestEndPos
            sStartIdx, sEndIdx = ".".join(map(str, lBestStartPos)), ".".join(map(str, lBestEndPos))
            self.oLogTextArea.see(sStartIdx)
            self.oLogTextArea.tag_config(CURRENT_SEARCH_TAG, background="green", foreground="white")
            self.oLogTextArea.tag_add(CURRENT_SEARCH_TAG, sStartIdx, sEndIdx)

    def startQueueProcessing(self):
        def doProcess():
            if self.bProcessQueue:
                lLines = []
                iTasks = 0
                try:
                    while True:
                        lLines += self.oQueue.get(False).splitlines()
                        iTasks += 1
                except Empty:
                    if lLines:
                        self.appendLogLines(lLines)
                        for _ in range(iTasks):
                            self.oQueue.task_done()
            self.master.after(500, doProcess)

        self.master.after(500, doProcess)

    def openNewSourceFile(self, sFilePath):
        sFilePath = os.path.normcase(os.path.abspath(sFilePath))
        if not os.path.isfile(sFilePath):
            tk.messagebox.showwarning("File not found", "File not found:\n%s" % sFilePath)
            return

        if sFilePath in self.lRecentSourceFiles:
            self.lRecentSourceFiles.remove(sFilePath)
        self.lRecentSourceFiles.insert(0, sFilePath)
        self.oSourceOptionMenu.updateChoices(self.lRecentSourceFiles)

        self.startFileWatch(sFilePath)

    def startFileWatch(self, sFilePath):
        self.stopFileWatch()
        self.clearLog()
        self.oQueue.queue.clear()
        self.oFileWatchThread = Thread(target=lambda: self.fileWatch(sFilePath))
        self.oFileWatchThread.start()

    def fileWatch(self, sFilePath):
        self.bWatchFile = True
        print("File watch started")
        try:
            with open(sFilePath, "r", encoding="utf-8") as oFile:
                while self.bWatchFile:
                    sContent = oFile.read()
                    if sContent:
                        self.oQueue.put(sContent)
                    else:
                        time.sleep(0.5)
        finally:
            print("File watch terminated")

    def stopFileWatch(self):
        if self.oFileWatchThread:
            self.bWatchFile = False
            self.oFileWatchThread.join()

    def clearLog(self):
        self.lExpressions = []
        with safeEdit(self.oLogTextArea) as w:
            w.delete("1.0", tk.END)

    def appendLogLines(self, lLines):
        lLines = filter(lambda s: bool(s), [s.rstrip("\n") for s in lLines])
        if lLines:
            iFirstExprIdx = len(self.lExpressions)
            for iIdx, sLine in enumerate(lLines):
                bIsExpr = self.oLogLineRegex.search(sLine) is not None
                if bIsExpr or not self.lExpressions:
                    oLogLevel = self.getLogLevel(sLine) if bIsExpr is not None else None
                    self.lExpressions.append(Expression(sLine, oLogLevel))
                else:
                    oLastExpr = self.lExpressions[-1]
                    oLastExpr.sText += "\n" + sLine
                    if iIdx == 0 and oLastExpr.bDisplay:
                        iFirstExprIdx -= 1
            self.updateLogWidget(iStartIdx=iFirstExprIdx)

    def getLogLevel(self, sLogExpr):
        for oLogLevel in self.lLogLevels:
            if oLogLevel.matches(sLogExpr):
                return oLogLevel

    def updateLogWidget(self, iStartIdx=0):
        iLinesCount = int(self.oLogTextArea.index(tk.END + "-1c").split(".")[0])
        iLastVisibleLineIdx = int(self.oLogTextArea.index("@0,%d" % self.oLogTextArea.winfo_height()).split(".")[0])
        bMustScroll = iLastVisibleLineIdx >= iLinesCount

        oFilterPattern = self.oFilterPattern
        lOldExpr, lExprToUpdate = self.lExpressions[:iStartIdx], self.lExpressions[iStartIdx:]
        iStartLineNumber = int(lOldExpr[-1].sEndIdx.split(".")[0]) if lOldExpr else 1
        with safeEdit(self.oLogTextArea) as w:
            w.delete("%d.0" % iStartLineNumber, tk.END)
            if iStartLineNumber > 1:
                w.insert(tk.END, "\n")
            for oExpr in lExprToUpdate:
                oExpr.bDisplay = False
                if oFilterPattern.matches(oExpr.sText):
                    if oExpr.oLogLevel is not None:
                        if oExpr.oLogLevel.bDisplay:
                            w.insert(tk.END, oExpr.sText + "\n", oExpr.oLogLevel.sTag)
                            oExpr.bDisplay = True
                    else:
                        w.insert(tk.END, oExpr.sText + "\n")
                        oExpr.bDisplay = True
                if oExpr.bDisplay:
                    iEndLineNumber = iStartLineNumber + 1 + oExpr.sText.count("\n")
                    oExpr.sStartIdx = "%d.0" % iStartLineNumber
                    oExpr.sEndIdx = "%d.0" % iEndLineNumber
                    iStartLineNumber = iEndLineNumber

        if bMustScroll:
            self.scrollToBottom()
        self.updateHighlighting(iStartIdx=iStartIdx)

    def scrollToBottom(self):
        self.oLogTextArea.see(tk.END)

    def setLogLevelDisplay(self, oLogLevel, bDisplay):
        oLogLevel.bDisplay = bDisplay
        self.updateLogWidget()

    def updateHighlighting(self, iStartIdx=0):
        lNewExprs = list(filter(lambda e: e.bDisplay,  self.lExpressions[iStartIdx:]))
        lTagNames = self.oLogTextArea.tag_names()

        oFilterPattern = self.oFilterPattern
        if lNewExprs and FILTER_TAG in lTagNames:
            self.oLogTextArea.tag_remove(FILTER_TAG, lNewExprs[0].sStartIdx, lNewExprs[-1].sEndIdx)
        self.oLogTextArea.tag_config(FILTER_TAG, foreground="white", background="red")

        oSearchPattern = self.oSearchPattern
        if lNewExprs and SEARCH_TAG in lTagNames:
            self.oLogTextArea.tag_remove(SEARCH_TAG, lNewExprs[0].sStartIdx, lNewExprs[-1].sEndIdx)
        self.oLogTextArea.tag_config(SEARCH_TAG, foreground="white", background="blue")

        for oExpr in lNewExprs:
            for iStartIdx, iEndIdx in oSearchPattern.getAllMatches(oExpr.sText):
                self.oLogTextArea.tag_add(SEARCH_TAG, "%s+%dc" % (oExpr.sStartIdx, iStartIdx),
                                          "%s+%dc" % (oExpr.sStartIdx, iEndIdx))
            for iStartIdx, iEndIdx in oFilterPattern.getAllMatches(oExpr.sText):
                self.oLogTextArea.tag_add(FILTER_TAG, "%s+%dc" % (oExpr.sStartIdx, iStartIdx),
                                          "%s+%dc" % (oExpr.sStartIdx, iEndIdx))


@contextmanager
def safeEdit(oTextWidget):
    oTextWidget.config(state=tk.NORMAL)
    try:
        yield oTextWidget
    except Exception:
        raise
    finally:
        oTextWidget.config(state=tk.DISABLED)
