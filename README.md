# Log Reader

A small application to visualize log files.

## Description

This is a small Tkinter application written in Python to open and visualize log files.
Log files are continuously watched in the background, making it suitable for monitoring log files as they are being
written.
Log levels are displayed in different colors. It is possible to filter by log level or regular expression. A small
search function is also implemented.

## Usage

`pythonw main.pyw`

## Development status

The application is still being built. Therefore all functionalities may not be available / implemented yet.
For now the only supported log format is the one used by [Karaf](https://karaf.apache.org/manual/latest/#_log).
