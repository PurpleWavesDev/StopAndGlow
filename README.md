# Stop and Glow - Toolset and DCC integrations for capturing and relighting images with Reflectance Transformation Imaging (RTI)

Warning: This implementation is for research purposes and lacks many features and proper integration with DCCs, as well as good documentation. Still WIP (if authors find motivation to continue the work).

## Stand-alone toolset
Create a Python virtual environment with the dependencies of `requirements.txt` / `requirements_linux.txt`. The recommended Python Version is 3.11. Capturing photos is only supported on Linux/Mac due to lack of support of gPhoto2 on Windows. Open the project folder with VSCode, the _Run and Debug_ sidebar has many commands available for all kind of purposes. You can launch `StopAndGlow.py` with your own commands that can be chained together for more complex tasks.

### Hardware-requirements for image capturing
- A lightdome controlled via DMX
- A USB-DMX interface
- A Canon DSLR (tested with EOS 90D) connected via USB
- Preferably a CUDA-supported GPU (Vulkan might work as well)

## Blender integration
You can launch the plugin with the VSCode extension _Blender Development [Experimental Fork]_. Open the Command Palette and type `Blender: Start`. A restart of Blender might be necessary after an inital start, where the scripts install missing dependencies in the Blender-Python environment.
