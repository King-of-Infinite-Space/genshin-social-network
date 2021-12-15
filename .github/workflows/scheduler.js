// this has been copied into scheduler.yml
module.exports = async ({ github, context }) => {
    const event = context.eventName
    console.log('Started on ' + event)
    const now = new Date()
    console.log(now.toString())
    let trigger = true
    if (event == 'schedule') {
        const dt = now - new Date(2021, 10, 24);
        const dd = Math.round(dt / (1000 * 60 * 60 * 24));
        console.log(Math.floor(dd/42) + ' days since last ver')
        trigger = !(dd % 21)
    }
    if (trigger) {
        await github.rest.repos.createDispatchEvent({
            owner: context.repo.owner,
            repo: context.repo.repo,
            event_type: event
        });
    }
}