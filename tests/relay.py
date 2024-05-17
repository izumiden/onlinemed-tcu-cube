# -*- coding: utf-8 -*-
import asyncio

import common
import tcu
import tcu.relay.client

argp = common.ArgumentParser()
args = argp.parse_args()

common.setlevel_for_root_logger(args)

logger = common.getLogger('tests')


async def run():
  logger.info("door_lock_async()")
  resp = await tcu.relay.client.door_lock_async(('192.168.1.103', 8893), 4500, 1000)
  logger.info(f"resp :{resp}")

  logger.info("door_lock()")
  resp = tcu.relay.client.door_lock(('192.168.1.103', 8893), 4500, 1000)
  logger.info(f"resp :{resp}")

asyncio.run(run())
