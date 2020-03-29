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

"""Tkinter utility functions."""

__author__ = "Quoc-Nam Dessoulles"
__email__ = "cokie.forever@gmail.com"
__license__ = "MIT"

import tkinter as tk
import tkinter.scrolledtext
from tkinter import ttk


def tkVar(oVar, oValue=None, xCallback=None):
    if oValue is not None:
        oVar.set(oValue)
    if xCallback is not None:
        oCallbackWrapper = CallbackWrapper(oVar.get(), xCallback)
        oVar.trace("w", lambda *args: oCallbackWrapper.fireIfNew(oVar.get()))
    return oVar


def stringVar(sValue=None, xCallback=None):
    return tkVar(tk.StringVar(), oValue=sValue, xCallback=xCallback)


def intVar(iValue=None, xCallback=None):
    return tkVar(tk.IntVar(), oValue=iValue, xCallback=xCallback)


def boolVar(bValue=None, xCallback=None):
    return tkVar(tk.BooleanVar(), oValue=bValue, xCallback=xCallback)


class CallbackWrapper:
    def __init__(self, oInitValue, xCallback):
        self.oValue = oInitValue
        self.xCallback = xCallback

    def fireIfNew(self, oValue):
        if oValue != self.oValue:
            self.oValue = oValue
            self.xCallback(oValue)


def label(oRoot, sText):
    return ttk.Label(oRoot, text=sText)


def button(oRoot, sText, xCallback=None):
    return ttk.Button(oRoot, text=sText, command=lambda *oArgs: xCallback() if xCallback else None)


def checkButton(oRoot, sText, bChecked=False, xCallback=None):
    oBoolVar = boolVar(bChecked, xCallback=xCallback)
    oButton = ttk.Checkbutton(oRoot, text=sText, variable=oBoolVar)
    # Keeping a reference is important to prevent garbage collection
    oButton.oBoolVar = oBoolVar
    return oButton


def optionMenu(oRoot, lChoices, sInitValue=None, xCallback=None):
    return OptionMenu(oRoot, lChoices, sInitValue=sInitValue, xCallback=xCallback)


class OptionMenu(ttk.OptionMenu):
    def __init__(self, oRoot, lChoices, sInitValue=None, xCallback=None):
        if sInitValue is None:
            sInitValue = lChoices[0] if lChoices else ""
        self.oStringVar = stringVar(sValue=sInitValue, xCallback=xCallback)
        super().__init__(oRoot, self.oStringVar, sInitValue, *lChoices)

    def updateChoices(self, lNewChoices, sInitValue=None):
        if sInitValue is None:
            sInitValue = lNewChoices[0] if lNewChoices else ""
        oMenu = self["menu"]
        oMenu.delete(0, tk.END)
        for sChoice in lNewChoices:
            oMenu.add_command(label=sChoice, command=lambda s=sChoice: self.oStringVar.set(s))
        self.oStringVar.set(sInitValue)


def entry(oRoot, sInitValue=None, iWidth=None, xCallback=None, bOnlyOnEnterPress=True):
    if bOnlyOnEnterPress:
        oStringVar = stringVar(sValue=sInitValue)
    else:
        oStringVar = stringVar(sValue=sInitValue, xCallback=xCallback)

    if iWidth:
        oEntry = ttk.Entry(oRoot, textvariable=oStringVar, width=iWidth)
    else:
        oEntry = ttk.Entry(oRoot, textvariable=oStringVar)

    if bOnlyOnEnterPress:
        def onPress(oKey):
            if oKey.char in ["\n", "\r"]:
                xCallback(oStringVar.get())

        oEntry.bind("<Key>", onPress)

    # Keeping a reference is important to prevent garbage collection
    oEntry.oStringVar = oStringVar
    return oEntry


def comboBox(oRoot, lValues, sInitValue=None, xCallback=None):
    if sInitValue is None:
        sInitValue = lValues[0] if lValues else ""
    oStringVar = stringVar(sValue=sInitValue, xCallback=xCallback)
    oComboBox = ttk.Combobox(oRoot, values=lValues, textvariable=oStringVar)
    # Keeping a reference is important to prevent garbage collection
    oComboBox.oStringVar = oStringVar
    return oComboBox


def scrolledText(oRoot, sInitValue=None):
    oScrolledText = tk.scrolledtext.ScrolledText(oRoot)
    if sInitValue:
        oScrolledText.insert(tkinter.END, sInitValue)
    return oScrolledText


class ScrolledText(tk.Text):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        xscrollbar = Scrollbar(master, orient=HORIZONTAL)
        xscrollbar.pack(side=BOTTOM, fill=X)

        yscrollbar = Scrollbar(master)
        yscrollbar.pack(side=RIGHT, fill=Y)

        text = Text(master, wrap=NONE,
                    xscrollcommand=xscrollbar.set,
                    yscrollcommand=yscrollbar.set)
        text.pack()

        xscrollbar.config(command=text.xview)
        yscrollbar.config(command=text.yview)


def findAll(sText, sExpr):
    iLen = len(sExpr)
    iStart = 0
    while True:
        iStart = sText.find(sExpr, iStart)
        if iStart == -1:
            return
        yield iStart
        iStart += iLen
