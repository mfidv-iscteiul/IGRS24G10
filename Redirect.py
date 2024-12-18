import sys
import KSR as KSR

def dumpObj(obj):           # List all obj attributes and methods
    for attr in dir(obj):
        KSR.info("obj attr = %s" % attr)
        if (attr != "Status"):
            KSR.info(" type = %s\n" % type(getattr(obj, attr)))
        else:
            KSR.info("\n")
    return 1

def mod_init():
    KSR.info("===== from Python mod init\n")
    return kamailio()

class kamailio:
    
    
    
    def __init__(self):
        KSR.info('===== kamailio.__init__\n')
        self.userStatus = {}
        
    def child_init(self, rank):
        KSR.info('===== kamailio.child_init(%d)\n' % rank)
        return 0
    
    def ksr_request_route(self, msg):
        KSR.info("Dom: " +KSR.pv.get("$fd") + "--")
        if  (msg.Method == "REGISTER"):
            KSR.info("REGISTER R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.info("            To: " + KSR.pv.get("$tu") +
                           " Contact: " + KSR.hdr.get("Contact") +"\n")
                
            if(KSR.pv.get("$fd") != "acme.pt" ):
                KSR.info("Acesso negado- Fora do dominio acme.pt \n")
                KSR.sl.send_reply(403, "Proibido - Dominio Invalido")
                return -1
            
            self.userStatus[KSR.pv.get("$fu")] = "Available"
            KSR.registrar.save('location', 0) #o 0 faz com o que save tenha o commportamento padrao 
            return 1

        if (msg.Method == "INVITE"):                      
            KSR.info("INVITE R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.info("        From: " + KSR.pv.get("$fu") +
                     "        To:   " + KSR.pv.get("$tu") +"\n")
            # KSR.info(KSR.pv.get("$td")+ " - z - " + KSR.pv.get("$fd"))

            # Requesito 1 - Pedido negado se vier se um dominio fora de acme.pt
            if(KSR.pv.get("$fd") != "acme.pt" ):
                KSR.info("Acesso negado- Fora do dominio acme.pt \n")
                KSR.sl.send_reply(403, "Proibido - Dominio Invalido")
                return -1
            
            # Requisito 2 - Encaminhamento exclusivo para outros funcionários da ACME
            if "acme.pt" not in KSR.pv.get("$td"):
                KSR.info("Acesso negado- Fora do dominio acme.pt \n")
                KSR.sl.send_reply(403, "Proibido - Dominio Invalido")
                return -1
            
            # Requisito 3 - Reencaminhamento para a sala de conferências ACME
            if KSR.pv.get("$ru") == "sip:conferencia@acme.pt" :
                KSR.info("A ser reencaminhado para a sala de conferências!")
                self.userStatus[KSR.pv.get("$fu")] = "inConference"
                KSR.pv.sets("$ru","sip:conferencia@127.0.0.1:5090")
                KSR.tm.t_relay()
                return 1
            
            # Requisito 4 - Funcionário destino não registado
            if KSR.registrar.lookup("location") != 1:
                KSR.info("Destinatário não se encontra registado ou disponível!\n")
                KSR.sl.send_reply(404, "Destinatário não se encontra registado ou disponível!")
                return -1
            
            
            # Requisito 5 - Funcionário destino ocupado (não em conferência) 
            if self.userStatus[(KSR.pv.get("$tu"))] == "Occupied":
                KSR.info("Destino ocupado - A redirecionar para o servidor de anúncios!")
                self.userStatus[KSR.pv.get("$fu")] = "Occupied" 
                KSR.pv.sets("$ru", "sip:busyann@127.0.0.1:5070")
                KSR.tm.t_relay()
                return 1
            
            # Requisito 6 - Funcionário destino em conferência
            if self.userStatus[(KSR.pv.get("$tu"))] == "inConference":
                KSR.info("Destino em conferência - A redirecionar para o servidor de anúncios!")
                self.userStatus[KSR.pv.get("$fu")] = "Occupied" 
                KSR.pv.sets("ru","sip:inconference@127.0.0.1:5080")
                


                if KSR.pv.get("$dtmf") == "0":
                    self.userStatus[KSR.pv.get("$fu")] = "inConference"
                    KSR.pv.set("ru","sip:conferencia@127.0.0.1:5090")
                    KSR.tm.t_relay()
                    return 1
                
                KSR.tm.t_relay()
                return 1
                

            self.userStatus[KSR.pv.get("$fu")] = "Occupied"
            self.userStatus[KSR.pv.get("$tu")] = "Occupied"
            KSR.tm.t_relay()
            return 1
        
        

        if (msg.Method == "ACK"):
            KSR.info("ACK R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.rr.loose_route()
            KSR.tm.t_relay()
            return 1

        if (msg.Method == "CANCEL"):
            KSR.info("CANCEL R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.registrar.lookup("location")
            KSR.tm.t_relay()
            return 1

        if (msg.Method == "BYE"):
            self.userStatus[KSR.pv.get("$fu")] = "Available"
            self.userStatus[KSR.pv.get("$tu")] = "Available"
            KSR.info("BYE R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.registrar.lookup("location")
            KSR.rr.loose_route()
            KSR.tm.t_relay()
            # Additional behaviour for BYE - sending a MESSAGE Request
            if (KSR.pv.get("$fd") == "a.pt"):
                KSR.pv.sets("$uac_req(method)", "MESSAGE")
                KSR.pv.sets("$uac_req(ruri)", KSR.pv.get("$fu")) # Send to ender
                KSR.pv.sets("$uac_req(turi)", KSR.pv.get("$fu"))
                KSR.pv.sets("$uac_req(furi)", "sip:kamailio@a.pt")
                KSR.pv.sets("$uac_req(callid)", KSR.pv.get("$ci")) # Keep the Call-ID
                msg = "You have ended a call"
                hdr = "Content-Type: text/plain\r\n" # More headers can be added
                KSR.pv.sets("$uac_req(hdrs)", hdr)
                KSR.pv.sets("$uac_req(body)", msg)
                KSR.uac.uac_req_send()
            return 1

        if (msg.Method == "MESSAGE"):
            KSR.info("MESSAGE R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.info("        From: " + KSR.pv.get("$fu") + " To:"+ KSR.pv.get("$tu") +"\n")
            if (KSR.pv.get("$rd") == "a.pt"):
                if (KSR.registrar.lookup("location") == 1):
                    KSR.info("  lookup changed R-URI: " + KSR.pv.get("$ru") +"\n")
                    KSR.tm.t_relay()
                else:
                    KSR.sl.send_reply(404, "Not found")
            else:
                KSR.rr.loose_route()
                KSR.tm.t_relay()
            return 1

    def ksr_reply_route(self, msg):
        KSR.info("===== response - from kamailio python script\n")
        KSR.info("      Status is:"+ str(KSR.pv.get("$rs")) + "\n");
        return 1

    def ksr_onsend_route(self, msg):
        KSR.info("===== onsend route - from kamailio python script\n")
        KSR.info("      %s\n" %(msg.Type))
        return 1

    def ksr_onreply_route_INVITE(self, msg):
        KSR.info("===== INVITE onreply route - from kamailio python script\n")
        return 0
 
    def ksr_failure_route_INVITE(self, msg):
        KSR.info("===== INVITE failure route - from kamailio python script\n")
        return 1
