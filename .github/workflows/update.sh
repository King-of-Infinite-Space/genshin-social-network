MSG=$(cat msg.log)
if [[ -z "$MSG" ]]; then
    echo "No changes to commit"
    exit
fi

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
if [[ "$MSG" == *"updating" ]]; then
    git restore utils/char_list.json
    git commit -a -m "$MSG"
    git push
    echo "Committed partial update"
    exit 1
else
    git commit -a -m "$MSG"
    git push
    echo "Committed full update"
fi