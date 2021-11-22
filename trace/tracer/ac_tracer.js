var temp = {
    steps: 0,
    stack: [{ops: []}],

    topMemory: function (log, start, stop) {
        return log.memory.slice(start, stop);
    },
    topStacks: function (log, n) {
        var stacks = [];
        n = n > log.stack.length() ? log.stack.length() : n;
        for (var i = 0; i < n; i++) {
            stacks.push(log.stack.peek(i).toString(16))
        }
        return stacks;
    },

    latestOpcodes: function (frame, count) {
        var start = frame["ops"].length - count;
        if (start < 0) {
            start = 0;
        }

        ops = []
        frame["ops"].slice(start, frame["ops"].length)
            .map(function (a) {
                ops.push(a["op"]);
            });
        return ops;
    },
    acList: [],

    addAddress: function (log, frame, address, op) {
        var slot = {
            contract: toHex(log.contract.getAddress()),
            op: op,
            address: address,
            depth: log.getDepth(),
            step: this.steps,
            preops: this.latestOpcodes(frame, 16),
            stacks: this.topStacks(log, 16)
        }
        this.acList.push(slot);
    },
    addSlot: function (log, frame, address, op, key) {
        var slot = {
            contract: address,
            op: op,
            address: address,
            key: key,
            depth: log.getDepth(),
            step: this.steps,
            preops: this.latestOpcodes(frame, 16),
            stacks: this.topStacks(log, 16)
        }
        this.acList.push(slot);
    },
    result: function () {
        return this.acList;
    },
    fault: function (log, db) {
    },
    step: function (log, db) {
        var frame = this.stack[this.stack.length - 1];
        var error = log.getError();
        if (error) {
            frame["error"] = error;
        } else if (log.getDepth() == this.stack.length) {
            var opinfo = {
                op: log.op.toString(),
                depth: log.getDepth()
            };
            if (frame.ops.length > 0) {
                var prevop = frame.ops[frame.ops.length - 1];
                if (prevop["op"].startsWith("PUSH")) {
                    prevop["op"] = prevop["op"] + " " + log.stack.peek(0).toString(16)
                }
            }
            switch (log.op.toString()) {
                case "CALL":
                case "CALLCODE":
                case "DELEGATECALL":
                case "STATICCALL":
                    opinfo["to"] = log.stack.peek(1).toString(16);
                    opinfo["ops"] = [];
                    this.stack.push(opinfo);
                    this.addAddress(log, frame, opinfo["to"], opinfo["op"])
                    break;
                case "EXTCODECOPY":
                case "EXTCODESIZE":
                case "EXTCODEHASH":
                case "BALANCE":
                    this.addAddress(log, frame, log.stack.peek(0).toString(16), opinfo["op"])
                    break;
                case "SLOAD":
                case "SSTORE":
                    opinfo["key"] = log.stack.peek(0).toString(16);
                    this.addSlot(log, frame, toHex(log.contract.getAddress()), opinfo["op"], opinfo["key"])
                    break;
            }
            frame.ops.push(opinfo);
        } else {
            this.stack = this.stack.slice(0, log.getDepth());
        }
        this.steps++;
    }
}
