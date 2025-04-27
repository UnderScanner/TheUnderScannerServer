# TheUnderScannerServer

This is the Flask backend server for serving 3D LiDAR scans to the **TheUnderScannerApp** Android app (cf [TheUnderScannerApp Repo](https://github.com/UnderScanner/TheUnderScannerApp)).

## Features

- Serve LiDAR scan files over HTTP
- Allow downloading of scan files
- Monitor and manage disk space for scans
- Calls `.sh` scripts to control the LiDAR

## Installation

### Requirements
- Python 3.8 or higher
- `virtualenv` for managing Python environments

### Setup

1.  Clone the repository
2.  Create a virtual environment
3.  Activate the virtual environment
4.  Install dependencies
5.  Configure the systemd service (Optional for automatic startup)

## Usage

The server serves files from the `Scans` folder stored on the host SBC.
