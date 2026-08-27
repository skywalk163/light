# -*- coding: utf-8 -*-
import asyncio

async def 长睡():
    await asyncio.sleep(60)

async def main():
    t = asyncio.create_task(长睡())
    t.cancel()
    接住 = False
    try:
        await t
    except Exception:
        接住 = True
    print('接住=', 接住)
    return 接住

接住 = asyncio.run(main())
print('接住(return)=', 接住)
