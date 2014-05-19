#!/usr/bin/python
#coding: utf8
from regmvv import *
from lxml import etree
from dbfpy import dbf
import timeit
import time
import fdb
import sys
class Profiler(object):
    def __enter__(self):
        self._startTime = time.time()
         
    def __exit__(self, type, value, traceback):
        print "Elapsed time:",time.time() - self._startTime # {:.3f} sec".format(time.time() - self._startTime)
def main():
#Обработка параметров
 #print len (sys.argv)
 if len(sys.argv)<=1:
  print ("getfromint: нехватает параметров\nИспользование: getfromint ФАЙЛ_КОНФИГУРАЦИИ")
  sys.exit(2)
 print sys.argv[1]
#Открытие файла конфигурации
 try:
  f=file(sys.argv[1])
 except Exception,e:
  print e
  sys.exit(2)
#Парсим xml конфигурации
 cfg = etree.parse(f) 
 #cfg.add_namespace(regmvv)
 cfgroot=cfg.getroot()
#Ищем параметры системы
 systemcodepage=cfgroot.find('codepage').text
#Ищем параметры базы
 dbparams=cfgroot.find('database_params')
 username=dbparams.find('username').text
 password=dbparams.find('password').text
 hostname=dbparams.find('hostname').text
 concodepage=dbparams.find('connection_codepage').text
 codepage=dbparams.find('codepage').text
 database=dbparams.find('database').text
 #print username,password,hostname,concodepage,codepage
#Ищем параметры МВВ
 mvv=cfgroot.find('mvv')
 agent_code=mvv.find('agent_code').text
 dept_code=mvv.find('dept_code').text
 agreement_code=mvv.find('agreement_code').text
 #f.close()
#Определяем тип и путь файла
 filepar=cfgroot.find('file')
 filecodepage=filepar.find('codepage').text
 output_path=filepar.find('output_path').text
 intput_path=filepar.find('input_path').text
 intput_arc_path=filepar.find('input_path_arc').text
 filetype=filepar.find('type').text
 filenum=filepar.find('numeric').text
 #Определение схемы файла должна быть ветка для типов файлов пока разбираем xml
 filescheme=filepar.findall('scheme')
 #создание root
 if filepar.find('result')<>'':
  print 'RES'
  fileresult=filepar.find('result')
  positiveresult=fileresult.find('negativeresult').text
  negativeresult=fileresult.find('positiveresult').text
  resultattrib='AnswerType'
 else:
  fileresult=''
 try:
  ans_scheme=filescheme[1].getchildren()[0]
 except:
  sys.exit(2)
 #Ищем поля ответа
 if filetype=='xml':
  #print ans_scheme.tag,ans_scheme.keys()
  #Проверяем явлется ли root контейнером ответов
  if 'answers' in ans_scheme.keys():
   ans=ans_scheme
  else:
   for ch in ans_scheme.getchildren():
    if ch.text=='reply_date':
     replydatetag=ch.tag
    if 'answers' in ch.keys():
     #print ch.tag
     answer=ch.getchildren()[0]
     answers=ch.tag
     break
  #Ищем поля сведений
  ansnodes=[]
  for ch in answer.getchildren(): #ограничение на кол-во ответов debug
   #ans2=[]
   if 'answer' in ch.keys():
    #Заполняем ключи для данных
    ans2={}
    if ch.attrib.values()[0]=='01': #Там где есть параметры это не приемлимо
     for chh in ch:
      for af in ansfields['01']:
       if chh.text==af:
        ans2[af]=chh.tag
    if ch.attrib.values()[0]=='11':
     chh=ch.getchildren()[0]
     #print "!!BUG",chh.tag
     ans2['right']=chh.tag #!!!
     for chh2 in chh:
      for af in ansfields['11']:
       #print "MM",chh2.text,chh2.tag
       if chh2.text==af:
        ans2[af]=chh2.tag #!bug
      if 'childrens' in chh2.attrib.keys():
       print "ADDR"
       for chh3 in chh2:
        for af in ansfields['11']:
         if chh3.text==af:
          #print af,ans2	
          ans2[af]=chh2.tag+':'+chh3.tag
    ansnodes.append([ch.tag,ch.attrib.values()[0],ans2])

  #print ansnodes
  #Ищем в значениях тег request_id
  for ch in answer.getchildren():
   print ch.tag,ch.text
   if ch.text=='request_id': 
    reqidtag=ch.tag
   #if ch.text=='reply_date': 
   # replydatetag=ch.tag 
    #print ch.tag
 #Соединяемся с базой ОСП
  try:
   con = fdb.connect (host=hostname, database=database, user=username, password=password,charset=concodepage)
  except  Exception, e:
   print("Ошибка при открытии базы данных:\n"+str(e))
   sys.exit(2)
  cur = con.cursor() 
 #Получить список файлов в папке input
  xmlfile=file(intput_path+'RR_092_06_12_13_1_reply.xml') #'rr4.xml')
  xml=etree.parse(xmlfile)
  xmlroot=xml.getroot()
  #print xmlroot.tag
  for ch in xmlroot.getchildren():
   if ch.text=='reply_date':
    replydatetag=ch.tag
  #Ищем контейнер ответов
  xmlanswers=xmlroot.find(answers)
 #Начинаем разбор ответов
  cn=0
  packid=getgenerator(cur,"DX_PACK")
  sqlbuff=[]
  sqltemp=''
  with Profiler() as p:
   for a in xmlanswers.getchildren():#[11:20]: #!Ограничение
    #Проверить запрос с этим id был или нет загружен
    request_id=a.find(reqidtag).text
    #print "Req_id",request_id,str(type(request_id))
    ipid=getipid(cur,'UTF-8','CP1251',request_id)
    #request_dt=a.find(replydatetag).text #reply_date      #    "06.12.2013" #???
    replydate=xmlroot.find(replydatetag).text
    if len(getanswertype(ansnodes,a))==0:
     #request_id=a.find(reqidtag).text
     #request_dt="06.12.2013"
     #print timeit.Timer("""
     #with Profiler() as p:
     sqltemp= setnegative(cur,'UTF-8','CP1251',agent_code,agreement_code,dept_code,request_id,replydate,packid) 
     for sqt in sqltemp:
      sqlbuff.append(sqt)
     #""").repeat(1)
    else:
     ans=getanswertype(ansnodes,a)
     #print "ANS",ans
     #print timeit.Timer("""
     sqltemp=setpositive(cur,con,'UTF-8','CP1251',agent_code,agreement_code,dept_code,request_id,replydate,ans,a,packid)
    for sqt in sqltemp:
     sqlbuff.append(sqt)
 
    #""").repeat(1)
    #print ans
    #print ans[0].values()
    #for i in range(len( ans)):
    # ans[i]
   #print len (xmlanswers),cn
   #print "first:"+xmlanswers.getchildren()[0].find(reqidtag).text,xmlanswers.getchildren()[0][3].text
   #print ipid,id
  print len(sqlbuff)
  #con.commit()
  with Profiler() as p:
   for sqt in sqlbuff:
    cur.execute(sqt)
   con.commit()
  xmlfile.close()
  f.close()
  con.close()
 if filetype=='xmlatrib':
  print ans_scheme.keys()
  answer=ans_scheme.getchildren()[0]  
  print answer.keys()
  
  #Ищем поля сведений
  ansnodes=[]
  for ch in answer.getchildren():
   if 'answers' in ans_scheme.keys():
    answer=ans_scheme.getchildren()[0]
    answers=ans_scheme.tag
   else:
    for ch in ans_scheme.getchildren():
    #if ch.text=='reply_date':
    # replydatetag=ch.tag
     if 'answers' in ch.keys():
      #print ch.tag
      answer=ch.getchildren()[0].attrib.keys()
      answers=ch.tag
      break
  print answers,answer.getchildren()[1].tag
  ans2={}
  answermatrix={}
  ch=answer.getchildren()[0]
  answermatrixatr=ch.attrib['answermatrix']
  for ch in answer:
   print 'X',ch.tag
   for chh in ch.attrib.keys():
    if  'answermatrix' ==chh:
     print ch.attrib['answermatrix'] 
     am=ch.attrib[ch.attrib['answermatrix']]
     at=ch.attrib['answer'] 
     answermatrix[am]=at
    print answermatrix
    
   print resultattrib ,str(answer.attrib[resultattrib]==positiveresult)
  #к параметров
  #разбор контейнеров
  xmlfile=file(intput_path+'PFR_20140507_12_09002_008_000_00010.xml') #'rr4.xml')
  xml=etree.parse(xmlfile)
  xmlroot=xml.getroot()
  print xmlroot.tag
  #Ищем контейнер ответов
  if(xmlroot.tag==answers):
   xmlanswers=xmlroot
  else:
   xmlanswers=xmlroot.find(answers)
  print answers
  print len(  xmlanswers.getchildren())
  for a in  xmlanswers.getchildren():
   print a.attrib[resultattrib]
   print answermatrix,a.attrib.keys()
   if (a.attrib[resultattrib]==positiveresult):
    aa=a.getchildren()[0]
    print answermatrix[ aa.attrib[answermatrixatr]]
    aaa=aa.getchildren()[0]
    print aaa.tag,aaa.attrib.keys()
 if filetype=='pfr':
  xmlfile=file(intput_path+'PFR_20140507_12_09002_008_000_00010.xml') #'rr4.xml')
  xml=etree.parse(xmlfile)
  xmlroot=xml.getroot()
  print xmlroot.tag
  #Ищем контейнер ответов
  answers='ExtAnswer'
  if(xmlroot.tag==answers):
   xmlanswers=xmlroot
  else:
   xmlanswers=xmlroot.findall(answers)
  print answers
  #print len(  xmlanswers.getchildren())
  cn=0
 # packid=getgenerator(cur,"DX_PACK")
  sqlbuff=[]
  sqltemp=''
  try:
   con = fdb.connect (host=hostname, database=database, user=username, password=password,charset=concodepage)
  except  Exception, e:
   print("Ошибка при открытии базы данных:\n"+str(e))
   sys.exit(2)
  cur = con.cursor()
  packid=getgenerator(cur,"DX_PACK")
  for a in  xmlanswers:
   print a.attrib.keys()
   #Проверить запрос с этим id был или нет загружен
   request_id=a.attrib['IPKey']
   #print "Req_id",request_id,str(type(request_id))
   #request_dt=a.find(replydatetag).text #reply_date      #    "06.12.2013" #???
   #actdate=a.attrib['ActDate']
   replydate='07.05.2014' #Пока задается вручную, надо издвлекать из файла
   #request_dt можно найти из запроса
   if a.attrib['AnswerType']=='1':
    print 'POS'
    #Разбор сведений
    for aa in a:
     print 'P', aa.keys(), aa.attrib['KindData']
     if aa.attrib['KindData']=='93':
      id=getgenerator(cur,"SEQ_DOCUMENT")
      ipid=getipid(cur,'UTF-8','CP1251',request_id)
      hsh=hashlib.md5()
      hsh.update(str(id))
      extkey=hsh.hexdigest()
      sqltemp=setresponse(cur,con,'UTF-8','CP1251',agent_code,agreement_code,dept_code,request_id,replydate,'01',id,packid,extkey,"Есть сведения")
      print sqltemp
      for sqt in sqltemp:
       sqlbuff.append(sqt)
       print sqt
      #Вставка сведений о статусе
      aaa=aa.getchildren()[0]
      print aaa.tag, aaa.attrib['State']
      debstate= aaa.attrib['State']
      cur.execute(("select * from ext_request where req_id="+request_id).decode('CP1251'))
      er=cur.fetchall()
      #print len(er)
      #datastr="Есть сведения"
      idnum=convtotype([' ','C'], getidnum(cur,'UTF-8','CP1251',ipid),'UTF-8','UTF-8')
      ent_name=convtotype([' ','C'],er[0][const["er_debtor_name"]],'UTF-8','UTF-8')
      #print str(type((ent_name)))
      ent_bdt=convtotype([' ','C'],er[0][const["er_debtor_birthday"]],'UTF-8','UTF-8')
      ent_by=ent_bdt.split('.')[2]
      ent_inn=convtotype([' ','C'],er[0][const["er_debtor_inn"]],'UTF-8','UTF-8')
      req_num=convtotype([' ','C'],er[0][const["er_req_number"]],'UTF-8','UTF-8')
      ipnum=convtotype([' ','C'],er[0][const["er_ip_num"]],'UTF-8','UTF-8')
      id=getgenerator(cur,"EXT_INFORMATION")
      hsh.update(str(id))
      svextkey=hsh.hexdigest()
      sq3="INSERT INTO EXT_INFORMATION (ID, ACT_DATE, KIND_DATA_TYPE, ENTITY_NAME, EXTERNAL_KEY, ENTITY_BIRTHDATE, ENTITY_BIRTHYEAR, PROCEED, DOCUMENT_KEY, ENTITY_INN) VALUES ("+str(id)+cln+quoted(replydate)+cln+quoted('08')+cln+quoted(ent_name)+cln+quoted(svextkey)+cln+quoted(ent_bdt)+cln+quoted(ent_by)+cln+quoted('0')+cln+quoted(extkey)+cln+quoted(ent_inn)+")"       #print sqltemp
      print sq3
      sq4="INSERT INTO EXT_DEBTOR_STATE_DATA (ID, STATE) VALUES ("+str(id)+cln+quoted(debstate)+");"
      print sq4
      sqlbuff.append(sq3)
      sqlbuff.append(sq4) 
     if aa.attrib['KindData']=='81':
      print 'Работа'
   else:
    sqltemp= setnegative(cur,'UTF-8','CP1251',agent_code,agreement_code,dept_code,request_id,replydate,packid)
    #print sqltemp
    for sqt in sqltemp:
     sqlbuff.append(sqt)
     print sqt
  #
  for sqt in sqlbuff:
   print sqt
   cur.execute(sqt)
  con.commit()
  xmlfile.close()
  f.close()
  con.close() 
   #if a.attrib['AnswerType']=='2':
   # print 'Negative'
   #else:
   # print 'Positive'
   

if __name__ == "__main__":
    main()
