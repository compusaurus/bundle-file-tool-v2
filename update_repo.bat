git -version
git init
git remote add origin git remote add origin https://github.com/compusaurus/bundle_file_tool_v2.git
git remote -v
git add .
git status
git commit -m "Update project with current local code"
git pull origin master -rebase
git push