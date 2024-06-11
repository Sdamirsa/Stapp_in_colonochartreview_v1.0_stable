# Project Aim
Creating a streamlit app for reviewing colonoscopy and pathology notes and filling in a form for specimens and colonoscopy quality

# Team
Me : ) with the longest name ever, Seyed Amir Ahmad Safavi-Naini

Josh Mohess

Ali Soroush

# Project Summary
1- We used streamlit to create an evaluation app

2- Then we used node js, stlite, and electron to package this into a portable .exe (for windows) and dmg (for mac)

# Acknowledgment and Developer Note: 
Hey folks :) Especial thank to stlite, electron, and streamlit team. Thanks to developers and maintainers of following contents (my resources): 
- https://github.com/whitphx/stlite/blob/main/packages/desktop/README.md  
- https://www.youtube.com/watch?v=3wZ7GRbr91g 
- https://www.electron.build/  

# Note for others

## How to build the app
After finishing your streamlit app, here is your path:

- 1- Install node.js 

- 2- Run "npm install" in the project folder 

- 3- Run "npm run dump "

- 4- Run "npm run serve"

- ! Note: There should be an app.py in the main folder (do not change the name or location as you should also change two other places. doesn't worth it : )

- If you did anything incorrectly, after changing the code, you should 
    - 1- remove the packages-lock.json and build/ and node_modlules 

    - 2-  do 2,3 again

- 5- Modify the package.json build key to define the target system (windows, linux, etc) and program type. Look at https://www.electron.build/

- 6- run npm dist

- 7- DONE :) In the dist folder you can find the file and folders (they will work together)

## Bugs and My debugs: 
- we should let user upload files and you cannot use the relative path to some external data, like csv
- json is not a good thing to save the data when you have multi-index complex dic. Use pickle for saving the data, and a txt file for user readability
- how to download data: you can't use relative paths to creat files, like pickle. For accessing files you should use st.download and create a download link. This happens due to the fact that your app will be run on a sandbox. This sandbox is an isolated enviroment and you can't access through it or take something out of it, unless you use st.upload and st.download

