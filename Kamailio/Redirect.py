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
        #KSR.info('===== kamailio.child_init(%d)\n' % rank)
        return 0
    
    def ksr_request_route(self, msg):
        
        if  (msg.Method == "REGISTER"):
            KSR.info("REGISTER R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.info("To: " + KSR.pv.get("$tu") + " Contact: " + KSR.hdr.get("Contact") +"\n")
                
            if(KSR.pv.get("$fd") != "acme.pt" ):
                KSR.info("Acesso negado- Fora do dominio acme.pt \n")
                KSR.sl.send_reply(403, "Proibido - Dominio Invalido")
                return -1
            
            self.userStatus[KSR.pv.get("$fu")] = "Available"
            KSR.info("Estado de " + KSR.pv.get("$fu") + " alterado para Available \n")
            KSR.registrar.save('location', 0) #o 0 faz com o que save tenha o commportamento padrao 
            return 1

        if (msg.Method == "INVITE"):                      
            KSR.info("INVITE R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.info("        From: " + KSR.pv.get("$fu") + "\n")
            KSR.info("          To: " + KSR.pv.get("$tu") + "\n")

            # Requesito 1 - Pedido negado se vier se um dominio fora de acme.pt
            if(KSR.pv.get("$fd") != "acme.pt" ):
                KSR.info("Acesso negado- Fora do dominio acme.pt \n")
                KSR.sl.send_reply(403, "Proibido - Dominio Invalido")
                return -1
            
            # Requisito 2 - Encaminhamento exclusivo para outros funcionários da ACME
            if (KSR.pv.get("$td") != "acme.pt" ):
                KSR.info("Acesso negado- Fora do dominio acme.pt \n")
                KSR.sl.send_reply(403, "Proibido - Dominio de destino Invalido")
                return -1
            
            # Requisito 3 - Reencaminhamento para a sala de conferências ACME
            if KSR.pv.get("$ru") == "sip:conferencia@acme.pt" :
                KSR.info("A ser reencaminhado para a sala de conferências! \n")
                
                self.userStatus[KSR.pv.get("$fu")] = "inConference"
                KSR.info("Estado de " + KSR.pv.get("$fu") + " alterado para inConference \n")
                
                KSR.pv.sets("$ru","sip:conferencia@127.0.0.1:5090")
                KSR.rr.record_route()
                KSR.tm.t_relay()
                return 1
            
            # Requisito 4 - Funcionário destino não registado
            if KSR.registrar.lookup("location") != 1:
                KSR.info("Destinatário não se encontra registado ou disponível! \n")
                KSR.sl.send_reply(404, "Destinatário não se encontra registado ou disponível!")
                return -1
            
            
            # Requisito 5 - Funcionário destino ocupado (não em conferência) 
            if self.userStatus[(KSR.pv.get("$tu"))] == "Occupied" :  #or self.userStatus[(KSR.pv.get("$u"))] == "Occupied"
                KSR.info("Destino ocupado - A redirecionar para o servidor de anúncios! \n")
                
                self.userStatus[KSR.pv.get("$fu")] = "Occupied"
                KSR.info("Estado de " + KSR.pv.get("$fu") + " alterado para Occupied \n")
                
                KSR.pv.sets("$ru", "sip:busyann@127.0.0.1:5070")
                KSR.rr.record_route()
                KSR.tm.t_relay()
                return 1
            
            # Requisito 6 - Funcionário destino em conferência
            if self.userStatus[(KSR.pv.get("$tu"))] == "inConference":
                KSR.info("Destino em conferência - A redirecionar para o servidor de anúncios! \n")
                
                #self.userStatus[KSR.pv.get("$fu")] = "Occupied"
                #KSR.info("Estado de " + KSR.pv.get("$fu") + " alterado para Occupied \n")
                
                KSR.pv.sets("$ru","sip:inconference@127.0.0.1:5080")
                KSR.rr.record_route()
                KSR.tm.t_relay()
                
                return 1
                
            #Chamada normal
            self.userStatus[KSR.pv.get("$fu")] = "Occupied"
            self.userStatus[KSR.pv.get("$tu")] = "Occupied"
            KSR.info("Estado de " + KSR.pv.get("$fu") + " e de " + KSR.pv.get("$tu") + " alterado para Occupied \n")
            
            KSR.rr.record_route()
            KSR.tm.t_relay()
            return 1
        
        

        if (msg.Method == "ACK"):
            KSR.info("ACK R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.tm.t_relay()
            return 1

        if (msg.Method == "INFO"):
            #Verificar se o ddestino está numa conferencia
            if (self.userStatus[(KSR.pv.get("$tu"))] == "inConference"):
                KSR.info("INFO recebido. Processando DTMF...\n")
                
                # Extrair o corpo da mensagem INFO
                dtmf_value = KSR.pv.get("$rb")  # $rb contém o corpo da mensagem SIP

                # Log para ver o valor recebido
                print(dtmf_value.split())
                KSR.info("DTMF recebido: " + dtmf_value + "\n")
                # Verificar se a tecla pressionada é '0'
                if dtmf_value.split()[0] == "Signal=0":
                    KSR.info("Tecla 0 pressionada - Redirecionando para a sala de conferências \n")
                    
                    KSR.pv.sets("$uac_req(method)", "INVITE")
                    KSR.pv.sets("$uac_req(ruri)", KSR.pv.get("$fu")) # Send to ender
                    KSR.pv.sets("$uac_req(turi)", KSR.pv.get("$fu"))
                    KSR.pv.sets("$uac_req(furi)", "sip:conferencia@acme.pt")
                    KSR.pv.sets("$uac_req(callid)", KSR.pv.get("$ci")) # Keep the Call-ID
                    # Adicionar o cabeçalho Contact
                    contact_value = "<sip:%s>" % KSR.pv.get("$fu")  # Definir como o próprio endereço de origem
                    hdr = "Contact: " + contact_value + "\r\n"
                    KSR.pv.sets("$uac_req(hdrs)", hdr)  # Cabeçalho Contact explícito
                    #hdr = "Content-Type: text/plain\r\n" # More headers can be added
                    #KSR.pv.sets("$uac_req(hdrs)", hdr)
                    KSR.uac.uac_req_send()
                    
                    return 1
                
                # Se não for a tecla esperada, apenas logar e não fazer nada
                KSR.info("Tecla DTMF não corresponde à ação configurada.\n")
                return -1
            
            else:
                # Se a mensagem info não estiver a vir de um user no servidor de anuncios "inconference"
                KSR.info("Serviço DTMF não configurado para servidores que não o inconference\n")
                return -1
        
        if (msg.Method == "CANCEL"):
            KSR.info("CANCEL R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.registrar.lookup("location")
            KSR.tm.t_relay()
            return 1

        if (msg.Method == "BYE"):
            KSR.info("BYE R-URI: " + KSR.pv.get("$ru") + "\n")
            
            self.userStatus[KSR.pv.get("$fu")] = "Available"
            self.userStatus[KSR.pv.get("$tu")] = "Available"
            KSR.info("Estado de " + KSR.pv.get("$fu") + " e de " + KSR.pv.get("$tu") + " alterado para Available \n")
            
            KSR.registrar.lookup("location")
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
                KSR.tm.t_relay()
            return 1

    def ksr_reply_route(self, msg):
        #KSR.info("===== response - from kamailio python script\n")
        #KSR.info("      Status is:"+ str(KSR.pv.get("$rs")) + "\n")
        
        reply_code = int(KSR.pv.get("$rs"))  # Obtém o código de resposta SIP
        KSR.info("Código de resposta obtido:  " + str(KSR.pv.get("$rs")) + "\n")
        
        # Verifica se o código da resposta é de uma chamada rejeitada
        if reply_code >= 400 and reply_code <= 499:
            KSR.info("Sessão rejeitada\n")
            
            self.userStatus[KSR.pv.get("$fu")] = "Available"
            self.userStatus[KSR.pv.get("$tu")] = "Available"
            KSR.info("Estado de " + KSR.pv.get("$fu") + " e de " + KSR.pv.get("$tu") + " alterado para Available \n")
            
            KSR.tm.t_relay()
            return -1
        
        return 1

    def ksr_onsend_route(self, msg):
        #KSR.info("===== onsend route - from kamailio python script\n")
        #KSR.info("      %s\n" %(msg.Type))
        return 1

    def ksr_onreply_route_INVITE(self, msg):
        #KSR.info("===== INVITE onreply route - from kamailio python script\n")
        return 0
 
    def ksr_failure_route_INVITE(self, msg):
        #KSR.info("===== INVITE failure route - from kamailio python script\n")
        return 1
