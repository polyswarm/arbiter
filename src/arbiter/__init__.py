# Listen to polyswarmd /bounties/pending route to find expired bounties
async def listen_and_arbitrate(isTest, backend):
    """Listens for bounties & vote reveals to establish ground truth"""
    if not check_address(address):
        # Always exit. Unusable with a bad address
        print_error(True, "Invalid address %s" % address, 7)

    scheduler = SchedulerQueue()
    scanner = backend.Scanner()
    headers = {'Authorization': api_key} if api_key else {}
    async with aiohttp.ClientSession(headers=headers) as session:
        if not await post_stake(session):
            # Always exit, because it is unusable without staking
            print_error(True, "Failed to Stake Arbiter.", 9)
        # Get the window length for phases
        voting_window = await get_vote_window(session)
        reveal_window = await get_reveal_window(session)
        if not voting_window or not get_reveal_window:
            # Cannot vote/settle without this info
            print_error(True, "Failed to get bounty windows.", 14)
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            while True:
                message = json.loads(await ws.recv())
                if message["event"] == "block":
                    await scheduler.execute_scheduled(message["data"]["number"])

                elif message["event"] == "bounty":
                    bounty = message["data"]
                    if not check_uuid(bounty["guid"]):
                        print_error(isTest, "Bad GUID: %s" % bounty["guid"], 10)
                        continue

                    verdicts = []
                    artifacts = await get_artifacts(session, isTest, bounty["uri"])
                    for i, f in enumerate(artifacts):
                        file = await get_artifact_contents(session, isTest, bounty["uri"], i)
                        if file is None:
                            print_error(isTest, "Failed to retrieve files from IPFS.", 12)
                            # If not exiting, just send zero
                            verdict.append(False)
                            continue

                        verdicts.append(await scanner.scan(file))

                    vote_task = SchedulerTask(int(bounty["expiration"])+reveal_window, post_vote, {"session": session, "isTest": isTest, "guid": bounty["guid"], "verdicts": verdicts})
                    settle_task = SchedulerTask(int(bounty["expiration"])+reveal_window+voting_window, post_settle, {"session": session, "isTest": isTest, "guid": bounty["guid"]})

                    await scheduler.schedule(vote_task)
                    await scheduler.schedule(settle_task)
