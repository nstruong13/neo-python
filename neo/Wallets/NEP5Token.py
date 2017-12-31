import binascii
import traceback

from decimal import getcontext, Decimal
from logzero import logger

from neo.Core.VerificationCode import VerificationCode
from neo.Cryptography.Crypto import Crypto
from neo.Prompt.Commands.Invoke import TestInvokeContract, test_invoke
from neo.Prompt.Utils import parse_param
from neo.UInt160 import UInt160
from neo.VM.ScriptBuilder import ScriptBuilder
from neo.Core.TX.TransactionAttribute import TransactionAttribute, TransactionAttributeUsage
import json
import pdb


class NEP5Token(VerificationCode):

    name = None
    symbol = None
    decimals = None

    _address = None

    def __init__(self, script=None):

        param_list = bytearray(b'\x07\x10')
        super(NEP5Token, self).__init__(script=script, param_list=param_list)

    def SetScriptHash(self, script_hash):
        self._scriptHash = script_hash

    @staticmethod
    def FromDBInstance(db_token):
        hash_ar = bytearray(binascii.unhexlify(db_token.ContractHash))
        hash_ar.reverse()
        hash = UInt160(data=hash_ar)
        token = NEP5Token(script=None)
        token.SetScriptHash(hash)
        token.name = db_token.Name
        token.symbol = db_token.Symbol
        token.decimals = db_token.Decimals
        return token

    @property
    def Address(self):
        if self._address is None:
            self._address = Crypto.ToAddress(self.ScriptHash)
        return self._address

    def Query(self, wallet):

        if self.name is not None:
            # don't query twice
            return

        sb = ScriptBuilder()
        sb.EmitAppCallWithOperation(self.ScriptHash, 'name')
        sb.EmitAppCallWithOperation(self.ScriptHash, 'symbol')
        sb.EmitAppCallWithOperation(self.ScriptHash, 'decimals')

        tx, fee, results, num_ops = test_invoke(sb.ToArray(), wallet, [])

        try:
            self.name = results[0].GetString()
            self.symbol = results[1].GetString()
            self.decimals = results[2].GetBigInteger()
            return True
        except Exception as e:
            logger.error("could not query token %s " % e)
        return False

    def GetBalance(self, wallet, address, as_string=False):

        addr = parse_param(address, wallet)
        if isinstance(addr, UInt160):
            addr = addr.Data
        sb = ScriptBuilder()
        sb.EmitAppCallWithOperationAndArgs(self.ScriptHash, 'balanceOf', [addr])

        tx, fee, results, num_ops = test_invoke(sb.ToArray(), wallet, [])

        try:
            val = results[0].GetBigInteger()
            precision_divisor = pow(10, self.decimals)
            balance = Decimal(val) / Decimal(precision_divisor)
            if as_string:
                formatter_str = '.%sf' % self.decimals
                balance_str = format(balance, formatter_str)
                return balance_str
            return balance
        except Exception as e:
            logger.error("could not get balance: %s " % e)
            traceback.print_stack()

        return 0

    def Transfer(self, wallet, from_addr, to_addr, amount):

        sb = ScriptBuilder()
        sb.EmitAppCallWithOperationAndArgs(self.ScriptHash, 'transfer',
                                           [parse_param(from_addr, wallet), parse_param(to_addr, wallet),
                                            parse_param(amount)])

        tx, fee, results, num_ops = test_invoke(sb.ToArray(), wallet, [], from_addr=from_addr)

        return tx, fee, results

    def TransferFrom(self, wallet, from_addr, to_addr, amount):
        invoke_args = [self.ScriptHash.ToString(), 'transferFrom',
                       [parse_param(from_addr, wallet), parse_param(to_addr, wallet), parse_param(amount)]]

        tx, fee, results, num_ops = TestInvokeContract(wallet, invoke_args, None, True)

        return tx, fee, results

    def Allowance(self, wallet, owner_addr, requestor_addr):
        invoke_args = [self.ScriptHash.ToString(), 'allowance',
                       [parse_param(owner_addr, wallet), parse_param(requestor_addr, wallet)]]

        tx, fee, results, num_ops = TestInvokeContract(wallet, invoke_args, None, True)

        return tx, fee, results

    def Approve(self, wallet, owner_addr, requestor_addr, amount):
        invoke_args = [self.ScriptHash.ToString(), 'approve',
                       [parse_param(owner_addr, wallet), parse_param(requestor_addr, wallet), parse_param(amount)]]

        tx, fee, results, num_ops = TestInvokeContract(wallet, invoke_args, None, True)

        return tx, fee, results

    def Mint(self, wallet, mint_to_addr, attachment_args):

        invoke_args = [self.ScriptHash.ToString(), 'mintTokens', []]

        invoke_args = invoke_args + attachment_args

        tx, fee, results, num_ops = TestInvokeContract(wallet, invoke_args, None, True, from_addr=mint_to_addr)

        return tx, fee, results

    def CrowdsaleRegister(self, wallet, register_addresses):

        invoke_args = [self.ScriptHash.ToString(), 'crowdsale_register', [parse_param(p, wallet) for p in register_addresses]]

        tx, fee, results, num_ops = TestInvokeContract(wallet, invoke_args, None, True)

        return tx, fee, results

    def ToJson(self):
        jsn = {
            'name': self.name,
            'symbol': self.symbol,
            'decimals': self.decimals,
            'script_hash': self.ScriptHash.ToString(),
            'contract address': self.Address
        }
        return jsn
