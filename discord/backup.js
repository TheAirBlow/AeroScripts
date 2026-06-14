// Discord Vencord DevTools script to export:
// 1. All friends and people with open DMs
// 2. All servers with folder info, join dates, and infinite invite URLs

(async () => {
    const output = {
        friends: [],
        dms: [],
        servers: [],
        generatedAt: new Date().toISOString()
    };

    const token = Vencord.Webpack.findByProps("getToken").getToken();
    const NoteStore = Vencord.Webpack.findByProps("getNote");

    console.log("Fetching DMs and friends...");

    const friendsList = new Map();
    const dmsList = new Map();

    function getAccountCreationTime(userId) {
        const discordEpoch = 1420070400000;
        const timestamp = (BigInt(userId) >> 22n) + BigInt(discordEpoch);
        return new Date(Number(timestamp)).toISOString();
    }

    function delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async function fetchWithRetry(url, options = {}) {
        while (true) {
            try {
                const response = await fetch(url, options);
                if (response.status === 429) {
                    const data = await response.json();
                    const retryAfter = (data.retry_after || 1) * 1000;
                    console.warn(`Rate limited. Waiting ${retryAfter}ms before retrying...`);
                    await delay(retryAfter);
                    continue;
                }
                return response;
            } catch (e) {
                return null;
            }
        }
    }

    async function fetchUserNote(userId) {
        const cached = await NoteStore.getNote();
        if (cached) {
            return cached.note;
        }

        const response = await fetchWithRetry(`https://discord.com/api/v9/users/@me/notes/${userId}`, {
            headers: { authorization: token, "Content-Type": "application/json" }
        });

        if (response && response.ok) {
            const data = await response.json();
            return data.note;
        }

        return undefined;
    }

    const relationships = RelationshipStore.getMutableRelationships();
    for (const [id, type] of relationships.entries()) {
        if (type === 1) {
            const user = UserStore.getUser(id);
            if (user) {
                friendsList.set(id, {
                    user_id: id,
                    channel_id: ChannelStore.getDMFromUserId(id) || null,
                    username: user.username,
                    display_name: user.globalName || user.displayName || user.username,
                    account_created: getAccountCreationTime(id),
                    friend_since: RelationshipStore.getSince(id),
                    note: await fetchUserNote(id)
                });
            }
        }
    }

    const openDMs = ChannelStore.getSortedPrivateChannels();
    for (const channel of openDMs) {
        if (channel.type === 1) {
            const userId = channel.recipients[0];
            const user = UserStore.getUser(userId);

            if (user) {
                if (friendsList.has(userId)) {
                    friendsList.get(userId).channel_id = channel.id;
                } else {
                    dmsList.set(userId, {
                        user_id: userId,
                        channel_id: channel.id,
                        username: user.username,
                        display_name: user.globalName || user.displayName || user.username,
                        created_at: getAccountCreationTime(userId),
                        friend_since: RelationshipStore.getSince(userId),
                        note: await fetchUserNote(userId)
                    });
                }
            }
        }
    }

    output.friends = Array.from(friendsList.values());
    output.dms = Array.from(dmsList.values());
    console.log(`Found ${output.friends.length} friends and ${output.dms.length} DM-only contacts`);

    console.log("Fetching servers...");

    const guilds = GuildStore.getGuilds();
    const folderData = UserSettingsProtoStore.getGuildFolders();

    const guildToFolderMap = new Map();
    folderData.forEach(folder => {
        if (folder.guildIds && Array.isArray(folder.guildIds)) {
            folder.guildIds.forEach(guildId => {
                let hexColor = null;
                if (folder.folderColor) {
                    hexColor = '#' + folder.folderColor.toString(16).padStart(6, '0');
                }

                guildToFolderMap.set(guildId, {
                    folder_id: folder.folderId,
                    folder_color: hexColor,
                    folder_name: folder.folderName || null
                });
            });
        }
    });

    if (guildToFolderMap.size > 0) {
        console.log(`Found ${guildToFolderMap.size} guilds in ${folderData.length} folders`);
    }

    async function getInviteUrl(guild) {
        await GuildActions.transitionToGuildSync(guild.id);
        await delay(1000);

        const channels = ChannelStore.getMutableGuildChannelsForGuild(guild.id);

        let targetChannel = Object.values(channels).find(c => {
            if (c.type !== 0 && c.type !== 5) return false;
            return PermissionStore.can(PermissionsBits.CREATE_INSTANT_INVITE, c);
        });

        if (!channelId) return null;

        try {
            const response = await fetchWithRetry(`/api/v9/channels/${channelId}/invites`, {
                method: "POST",
                headers: { authorization: token, "Content-Type": "application/json" },
                body: JSON.stringify({
                    max_age: 0,
                    max_uses: 0,
                    target_type: null,
                    temporary: false,
                    flags: 0
                })
            });

            if (response && response.ok) {
                const data = await response.json();
                return `https://discord.gg/${data.code}`;
            }
        } catch (e) {}

        return null;
    }

    const servers = [];
    const guildArray = Object.values(guilds);

    for (const guild of guildArray) {
        const folderInfo = guildToFolderMap.get(guild.id) || {
            folder_id: null,
            folder_color: null,
            folder_name: null
        };

        let inviteUrl = guild.vanityURLCode ? `https://discord.gg/${guild.vanityURLCode}` : await getInviteUrl(guild);

        servers.push({
            guild_id: guild.id,
            name: guild.name,
            joined_at: guild.joinedAt ? new Date(guild.joinedAt).toISOString() : null,
            folder_id: folderInfo.folder_id,
            folder_color: folderInfo.folder_color,
            folder_name: folderInfo.folder_name,
            invite_url: inviteUrl,
            member_count: GuildMemberCountStore.getMemberCount(guild.id)
        });
    }

    output.servers = servers.sort((a, b) => a.name.localeCompare(b.name));
    console.log(`Found ${output.servers.length} servers`);

    const jsonOutput = JSON.stringify(output, null, 2);
    console.log(jsonOutput)

    const blob = new Blob([jsonOutput], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `discord_backup_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    console.log("Backup file triggered for download.");
})();
