// This tracer organizes access lists by contract calls
var temp = {
    // transfer, call or create
    type: 0,
    error: '',
    acList: {},
    touches: 0,
    jumpis: 0,
    depth: 0,
    callStack: [],
    tmp: [],
    formalizeAddress: function (address) {
        // this.tmp.push(address)
        if (address.startsWith("0x")) {
            return address;
        } else if (address.length > 40) {
            // sometimes, invalid address in stack
            return ""
        }
        return "0x" + '0'.repeat(40 - address.length) + address
    },

    getCurContractFuncAcList: function (curContract) {
        var curFunc = this.callStack[this.depth];
        var curContractAcList;
        var curContractFuncAclist;

        if (curContract in this.acList) {
            curContractAcList = this.acList[curContract];
        } else {
            curContractAcList = {};
            this.acList[curContract] = curContractAcList;
        }

        if (curFunc in curContractAcList) {
            curContractFuncAclist = curContractAcList[curFunc];
        } else {
            curContractFuncAclist = {"s": {}};
            curContractAcList[curFunc] = curContractFuncAclist;
        }
        return curContractFuncAclist;
    },

    addAddress: function (curContract, address, func) {
        var addressFuncs = {};
        var curContractFuncAclist = this.getCurContractFuncAcList(curContract);

        if (address in curContractFuncAclist) {
            addressFuncs = curContractFuncAclist[address];
        } else {
            curContractFuncAclist[address] = addressFuncs;
        }

        if (func !== "" && !(func in addressFuncs)) {
            addressFuncs[func] = "";
        }
    },

    addSlot: function (curContract, key) {
        var curContractFuncAclist = this.getCurContractFuncAcList(curContract);
        if (!(key in curContractFuncAclist["s"])) {
            curContractFuncAclist["s"][key] = "";
        }
    },

    result: function (ctx, db) {
        if (this.type > 0) {
            // Even for a simple transfer, ctx['type'] == 'CALL'
            if (ctx['type'] === 'CREATE') {
                this.type = 2
            }
            this.addAddress(toHex(ctx['to']), toHex(ctx['from']), "")
        } else {
            this.acList[toHex(ctx['from'])] = {}
            this.acList[toHex(ctx['to'])] = {}
        }

        // transaction success
        var status = 1
        if (this.error.length > 0) {
            // transaction failed
            status = 0
        }

        return {
            type: this.type,
            jumpis: this.jumpis,
            tt: this.touches,
            acl: this.acList,
            st: ctx['time'],
            status: status,
            tmp: this.tmp
        }
    },
    fault: function (log, db) {
        this.error = log.getError()
    },
    enter: function (callFrame) {
        this.callStack.push((toHex(callFrame.getInput())).substring(0, 10));
        this.depth++
        // this.tmp.push("Enter " + callFrame.getType() + " " + toHex(callFrame.getTo()) + " : " + this.callStack[this.depth])
    },
    exit: function (frameResult) {
        this.callStack.pop();
        this.depth--
        // this.tmp.push("Exit")
    },
    step: function (log, db) {
        if (this.type == 0) {
            // initialize
            this.type = 1;
            this.callStack.push((toHex(log.contract.getInput())).substring(0, 10));
        }
        if (log.getError()) {
            this.error = log.getError()
            return
        }
        switch (log.op.toString()) {
            case "CALL":
            case "CALLCODE":
                var address = this.formalizeAddress(log.stack.peek(1).toString(16));
                if (address.length == 42) {
                    var instart = log.stack.peek(3).valueOf();
                    var func = toHex(log.memory.slice(instart, instart + 4));
                    this.addAddress(toHex(log.contract.getAddress()), address, func);
                    this.touches = this.touches + 1;
                }
                break;
            case "DELEGATECALL":
            case "STATICCALL":
                var address = this.formalizeAddress(log.stack.peek(1).toString(16))
                if (address.length == 42) {
                    var instart = log.stack.peek(2).valueOf();
                    var func = toHex(log.memory.slice(instart, instart + 4));
                    this.addAddress(toHex(log.contract.getAddress()), address, func);
                    this.touches = this.touches + 1;
                }
                break;
            case "EXTCODECOPY":
            case "EXTCODESIZE":
            case "EXTCODEHASH":
            case "BALANCE":
            case "SELFDESTRUCT":
                var addr = this.formalizeAddress(log.stack.peek(0).toString(16));
                if (addr.length == 42) {
                    this.addAddress(toHex(log.contract.getAddress()), addr, "");
                    this.touches = this.touches + 1;
                }
                break;
            case "SLOAD":
                // case "SSTORE":
                // this address has 0x prefix, but slot has no 0x prefix
                this.addSlot(toHex(log.contract.getAddress()), log.stack.peek(0).toString(16));
                this.touches = this.touches + 1;
                // this.tmp.push("Sload " + toHex(log.contract.getAddress()) + " " + log.stack.peek(0).toString(16))
                break;
        }
    }
}
