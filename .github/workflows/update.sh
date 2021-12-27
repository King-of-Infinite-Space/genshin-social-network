MSG=$(cat msg.log)
if [[ -z "$MSG" ]]; then
    echo "No changes to commit"
elif [[ "$MSG" == *"updating" ]]; then
    git restore utils/char_list.json
    git commit -a -m "$MSG" --author="github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>"
    git push
    echo "Committed partial update"
    exit 1
else
    git commit -a -m "$MSG" --author="github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>"
    git push
    echo "Committed full update"
fi