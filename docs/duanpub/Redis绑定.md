# Redis绑定

> Redis底层协议绑定：管道/事务/Lua脚本/Stream/Geo/位图/HyperLogLog/哨兵/集群

## 包信息

| 属性 | 值 |
|------|-----|
| 版本 | 1.0.0 |
| 分类 | 开发工具 |
| 优先级 | 🔹 扩展包 |
| 公开函数 | 90 |
| FFI 声明 | 13 |

**关键词:** Redis, 管道, 事务, Lua, Stream, 集群, 哨兵, Geo, 位图, HyperLogLog

## 导入方式

```duan
导入 Redis绑定
```

或

```duan
导入 标准Redis绑定
```

## 函数列表

共 90 个公开函数

### checkRedisConn

*暂无详细文档*

### doReconnect

*暂无详细文档*

### buildRESPCommand

*暂无详细文档*

### escapeRESPArg

*暂无详细文档*

### parseRESPReply

*暂无详细文档*

### execRawCmd

*暂无详细文档*

### execArgCmd

*暂无详细文档*

### encodeRESP

*暂无详细文档*

### decodeRESP

*暂无详细文档*

### connectRedis

*暂无详细文档*

### closeRedis

*暂无详细文档*

### setAutoReconnect

*暂无详细文档*

### setTimeout

*暂无详细文档*

### enableKeepAlive

*暂无详细文档*

### execCommand

*暂无详细文档*

### execCommandWithArgs

*暂无详细文档*

### getError

*暂无详细文档*

### createPipeline

*暂无详细文档*

### pipelineAddCmd

*暂无详细文档*

### pipelineAddCmdArgs

*暂无详细文档*

### pipelineExec

*暂无详细文档*

### pipelineGetResults

*暂无详细文档*

### pipelineReset

*暂无详细文档*

### createTransaction

*暂无详细文档*

### txBegin

*暂无详细文档*

### txWatch

*暂无详细文档*

### txAddCmd

*暂无详细文档*

### txExec

*暂无详细文档*

### txDiscard

*暂无详细文档*

### evalScript

*暂无详细文档*

### evalShaScript

*暂无详细文档*

### loadScript

*暂无详细文档*

### scriptExists

*暂无详细文档*

### flushScriptCache

*暂无详细文档*

### killScript

*暂无详细文档*

### pSubscribe

*暂无详细文档*

### pUnsubscribe

*暂无详细文档*

### publish

*暂无详细文档*

### listActiveChannels

*暂无详细文档*

### channelNumSub

*暂无详细文档*

### numPatternSub

*暂无详细文档*

### xadd

*暂无详细文档*

### xread

*暂无详细文档*

### xreadMulti

*暂无详细文档*

### xrange

*暂无详细文档*

### xgroupCreate

*暂无详细文档*

### xreadgroup

*暂无详细文档*

### xack

*暂无详细文档*

### xlen

*暂无详细文档*

### xdel

*暂无详细文档*

### geoAdd

*暂无详细文档*

### geoAddBatch

*暂无详细文档*

### geoGet

*暂无详细文档*

### geoDist

*暂无详细文档*

### geoRadius

*暂无详细文档*

### geoRadiusByMember

*暂无详细文档*

### geoHash

*暂无详细文档*

### setBit

*暂无详细文档*

### getBit

*暂无详细文档*

### bitCount

*暂无详细文档*

### bitOp

*暂无详细文档*

### bitPos

*暂无详细文档*

### pfadd

*暂无详细文档*

### pfcount

*暂无详细文档*

### pfmerge

*暂无详细文档*

### createSentinel

*暂无详细文档*

### sentinelDiscoverMaster

*暂无详细文档*

### sentinelGetMasterInfo

*暂无详细文档*

### sentinelFailover

*暂无详细文档*

### closeSentinel

*暂无详细文档*

### createCluster

*暂无详细文档*

### clusterBuildConnMap

*暂无详细文档*

### clusterCalcSlot

*暂无详细文档*

### clusterGetNode

*暂无详细文档*

### clusterExec

*暂无详细文档*

### clusterNodes

*暂无详细文档*

### clusterInfo

*暂无详细文档*

### clusterSlots

*暂无详细文档*

### closeCluster

*暂无详细文档*

### setKey

*暂无详细文档*

### getKey

*暂无详细文档*

### delKey

*暂无详细文档*

### existsKey

*暂无详细文档*

### expireKey

*暂无详细文档*

### ttlKey

*暂无详细文档*

### randomKey

*暂无详细文档*

### keyType

*暂无详细文档*

### renameKey

*暂无详细文档*

### incr

*暂无详细文档*

### ping

*暂无详细文档*
