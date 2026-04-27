cd ./src/content/

grep -rl '^https://github.com/user-attachments/assets/' . \
  | xargs sed -i '' -E 's|^(https://github.com/user-attachments/assets/.*)|<video src="\1" width="600" controls />|'

cd ../../
