# Task definition

* We are developing a CLI utility in Python using the Click library.
* The purpose of the utility is to automate assembly and layout of a standalone document from the set Markdown files which are structured in a tree-like directory structure.
* The task of Python scripts is to prepare the separate files for the layout, and the layout itself and the final document will be dealt with pandoc.
* The name of the utility is `pandocster`.

## Features

* Pandocster should be able to check its environment and dependencies to verify that pandoc is installed, available in the PATH, and that the version is compatible with the project.
* Pandocster should be able to calculate the levels of the headers in markdown files according to the directory structure and the rules of the project.
* Pandocster should treat files named `_index.md` in any as a main header of the section and calculate the levels of the all other headers in the section based on the level of the main header.
* Pandocster should be able to convert relative hyperlinks and reference-style links in markdown files before layout so that the links are correct and work after layout in the final document.
* Pandocster should be able to convert inline images in markdown files before layout so that the images are correct and work after layout in the final document.
* Pandocster should have a configuration file in ~/.config/pandocster/config.yaml which will contain the default rules of the project and the layout of the final document.
* Pandocster should use the configuration file config.yaml from the current directory if it exists, otherwise use the configuration file from ~/.config/pandocster/config.yaml.
* Pandocster should have a way to pass the location of the configuration file as an argument to the command.
