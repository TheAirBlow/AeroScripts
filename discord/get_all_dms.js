// this script fetches the list of people with who you have opened DMs plus friends and produces a JSON like this:
// [{"user_id": 0, "channel_id": 0, "username": "", "display_name": ""}, ...]

(() => {
    const masterList = new Map();

    const relationships = RelationshipStore.getMutableRelationships();
    relationships.forEach((type, id) => {
        if (type === 1) {
            const user = UserStore.getUser(id);
            if (user) {
                masterList.set(id, {
                    user_id: id,
                    channel_id: ChannelStore.getDMFromUserId(id) || null,
                               username: user.username,
                               display_name: user.globalName || user.displayName || user.username
                });
            }
        }
    });

    const openDMs = ChannelStore.getSortedPrivateChannels();
    openDMs.forEach(channel => {
        if (channel.type === 1) {
            const userId = channel.recipients[0];
            const user = UserStore.getUser(userId);

            if (!masterList.has(userId) && user) {
                masterList.set(userId, {
                    user_id: userId,
                    channel_id: channel.id,
                    username: user.username,
                    display_name: user.globalName || user.displayName || user.username
                });
            } else if (masterList.has(userId)) {
                masterList.get(userId).channel_id = channel.id;
            }
        }
    });

    const finalData = Array.from(masterList.values());
    const jsonOutput = JSON.stringify(finalData);
    console.log(jsonOutput);
    copy(jsonOutput);
})();
