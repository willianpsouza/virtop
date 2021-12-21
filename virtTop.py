#!/usr/bin/python

import subprocess
import re
import sys
import json
import time
import sys
import psutil

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_ProcessID(vmname):
    processpath=("/var/run/libvirt/qemu/%s.pid" % (vmname.strip()))
    f = open(processpath,'r')
    processid=f.read()
    f.close()
    return processid.strip()

def get_CpuUsageByProcessID(processid):
    p = psutil.Process(int(processid))
    vutcpu=p.cpu_percent(0.1)
    return vutcpu

def get_MemoryByProcessID(processid):
    p = psutil.Process(int(processid))
    raminuse = p.memory_info()[0] / float(2 ** 20)
    return raminuse	

def get_ExtendedInfoByProcessID(processid):
    dret = {}
    ##### PATH PARA AS INFORMACOES DE MEMORIA DO PROCESSO
    processpath=("/proc/%s/status" % (processid))
    f = open(processpath,'r')
    f1=f.readlines()
    for line in f1:
        dados=re.split("\s+",line)
        if(re.search(r'^VmSwap',dados[0])):
            memory_swap=float(float(dados[1]*1)*1024)
        if(re.search(r'^VmPeak',dados[0])):
            memory_peak=float(float(dados[1]*1)*1024)
        if(re.search(r'ctxt_switches',dados[0])):
            context_switch=int(dados[1]*1)
    f.close()    
    dret['swap_process']=memory_swap
    dret['memopeak']=memory_peak
    dret['context_switch']=context_switch
    return dret

def main ():
	wrlocal=0
	rrlocal=0
	wrtotal=0
	rrtotal=0
	wrsoma=0
	rrsoma=0
	wfirst=1
	vmx = {}
	vmsw = {}
	vmsr = {}
	vmtp = {}
	vmsctxtsw = {}
	rx = {}
	tx = {}
	txlocal = 0
	rxlocal = 0
	rxsoma = 0
	txsoma = 0
	tms = 0

	vmsctxtswlocal = 0
	vmsctxtswsoma = 0
	imprimir=""
	cputotal=0
	cpulocal=0
	memolocal=0
	memototal=0
	vmachines=0
	total_iops = 0
	total_ctxs = 0

	while( 1 == 1 ):
		print(chr(27) + "[2J")
		print("XTotal de vms:",vmachines,"Total de vcpus: ",cputotal , "Total de memoria:", memototal , "IOPS", total_iops, "CTXS", total_ctxs)
		print(imprimir)
		
		imprimir=""
		cputotal=0
		memototal=0
		vmachines=0

		total_iops = 0
		total_ctxs = 0

		vms = subprocess.Popen(['virsh', 'list', '--name'],stdout=subprocess.PIPE).communicate()[0]
		for vm in vms.splitlines():
			vm = vm.decode('utf-8')

			if re.search(r'^$',vm): continue

			vmnprocessid = get_ProcessID(vm)
			hostcpusage = get_CpuUsageByProcessID(vmnprocessid)
			procura = vm
			wrlocal=0
			rrlocal=0
			txlocal=0
			rxlocal=0
			cpulocal=0
			memolocal=0
			memoswap=0
			memopeak=0
			vmachines+=1
			processid=0
		
			#### SE A LINHA FOR EM BRANCO CONTINUE
			if re.search(r'^$',vm):
				continue

			##### PATH PARA O PID DO PROCESSO
			processpath="/var/run/libvirt/qemu/" +  procura + ".pid"
			f = open(processpath,'r')
			processid=f.read()
			f.close()

			##### PATH PARA AS INFORMACOES DE MEMORIA DO PROCESSO
			processpath="/proc/" +  processid + "/status"
			f = open(processpath,'r')
			f1=f.readlines()
			for line in f1:
				dados=re.split("\s+",line)
				if(re.search(r'^VmSwap',dados[0])):
					memoswap=float(float(dados[1]*1)/1024/1024)
				if(re.search(r'^VmPeak',dados[0])):
					memopeak=float(float(dados[1]*1)/1024/1024)
				if(re.search(r'ctxt_switches',dados[0])):
					vmsctxtswlocal=int(dados[1]*1)
			f.close()

			output = subprocess.Popen(['virsh', 'domstats', procura],stdout=subprocess.PIPE).communicate()[0]
			for line in output.splitlines():
				line = line.decode('utf-8')
				dados=re.split("=",line)
				if(re.search(r'rd\.reqs',dados[0])):
					rrlocal+=int(dados[1]*1)

				if(re.search(r'wr\.reqs',dados[0])):
					wrlocal+=int(dados[1]*1)

				if(re.search(r'vcpu\.current',dados[0])):
					cputotal+=int(dados[1]*1)
					cpulocal+=int(dados[1]*1)

				if(re.search(r'balloon\.maximum',dados[0])):
					memototal+=int(int(dados[1]*1)/1024/1024)
					memolocal+=float(float(dados[1]*1)/1024/1024) # INFORMACAO JA VEM EM KILO

				if(re.search(r'rx\.bytes',dados[0])):
					rxlocal+=float(float(dados[1]*1)/1024/1024)*4.85

				if(re.search(r'tx\.bytes',dados[0])):
					txlocal+=float(float(dados[1]*1)/1024/1024)*4.85

			if(wfirst == 1):
				vmtp[procura]=time.time()
				tms = 1
				vmsw[procura]=wrlocal
				vmsr[procura]=rrlocal
				vmsctxtsw[procura]=vmsctxtswlocal

				rx[procura]=rxlocal
				tx[procura]=txlocal
			else:
				tms = time.time() - vmtp[procura]
				tms = tms*1
				vmtp[procura] = time.time()

				wrsoma=(wrlocal - vmsw[procura])/tms
				rrsoma=(rrlocal - vmsr[procura])/tms
				vmsctxtswsoma = vmsctxtswlocal - vmsctxtsw[procura]

				rxsoma = (rxlocal - rx[procura])/tms
				txsoma = (txlocal - tx[procura])/tms

				nome=" %41s " % procura[0:40]
				if(wrsoma > 100):
					writes=bcolors.FAIL + " %4s w/s" % "{:4.0f}".format(wrsoma) + bcolors.ENDC
				elif(wrsoma > 50):
					writes=bcolors.WARNING + " %4s w/s" % "{:4.0f}".format(wrsoma) + bcolors.ENDC					
				else:
					writes=bcolors.OKGREEN + " %4s w/s" % "{:4.0f}".format(wrsoma) + bcolors.ENDC

				if(rrsoma > 100):
					reads=bcolors.FAIL +" %4s r/s" % "{:4.0f}".format(rrsoma) + bcolors.ENDC
				elif(rrsoma > 50):
					reads=bcolors.WARNING +" %4s r/s" % "{:4.0f}".format(rrsoma) + bcolors.ENDC					
				else:
					reads=bcolors.OKGREEN +" %4s r/s" % "{:4.0f}".format(rrsoma) + bcolors.ENDC

				if(hostcpusage > 100):
					phostcpusage=bcolors.FAIL +"%3s" % "{:3.0f}".format(int(hostcpusage)) + bcolors.ENDC
				elif(hostcpusage > 50):
					phostcpusage=bcolors.WARNING +"%3s" % "{:3.0f}".format(int(hostcpusage)) + bcolors.ENDC					
				else:
					phostcpusage=bcolors.OKGREEN +"%3s" % "{:3.0f}".format(int(hostcpusage)) + bcolors.ENDC

				pvmsctxt=" CTXS: %s/s" % "{:02d}".format(vmsctxtswsoma)
				cpus="Cpu/z:%2s/%3s " % (cpulocal,phostcpusage)
				pid="Pid: %8s " % processid

				if(memoswap > 1.100):
					pmemoswap=bcolors.FAIL + "%2s"  % "{:02d}".format(int(memoswap)) + bcolors.ENDC
				elif(memoswap > 0.100):
					pmemoswap=bcolors.WARNING + "%2s" % "{:02d}".format(int(memoswap)) + bcolors.ENDC
				else:
					pmemoswap="%2s" % "{:02d}".format(int(memoswap))

				pmemolocal="M/S/X: %3s|%3s|%3s" % ("{:03d}".format(int(memolocal)),pmemoswap,"{:02d}".format(int(memopeak)))

				prx=" tx/rx %3s/%3s Mb/s" % ("{:03d}".format(int(rxsoma)),"{:03d}".format(int(txsoma)))

				imprimir=''.join([imprimir,pid,nome])
				imprimir=''.join([imprimir,cpus,pmemolocal])
				imprimir=''.join([imprimir,writes,reads,pvmsctxt])
				imprimir=''.join([imprimir,prx])
				imprimir=''.join([imprimir,'\n'])

				vmsw[procura]=wrlocal
				vmsr[procura]=rrlocal
				vmsctxtsw[procura]=vmsctxtswlocal

				rx[procura]=rxlocal
				tx[procura]=txlocal

				total_ctxs+=int(vmsctxtswsoma)
				total_iops+=int(wrsoma)
				total_iops+=int(rrsoma)

		wfirst=0
		time.sleep(1)

try:
	main()
except KeyboardInterrupt:
	pass
