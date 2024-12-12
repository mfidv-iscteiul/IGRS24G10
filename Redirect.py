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

    def child_init(self, rank):
        KSR.info('===== kamailio.child_init(%d)\n' % rank)
        return 0
    
    def ksr_request_route(self, msg):
        if  (msg.Method == "REGISTER"):
            KSR.info("REGISTER R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.info("            To: " + KSR.pv.get("$tu") +
                           " Contact:"+ KSR.hdr.get("Contact") +"\n")
            if(KSR.pv.get("$fd") != "acme.pt" ):
                KSR.info("Acesso negado- Fora do dominio acme.pt \n")
                KSR.sl.send_reply(403, "Proibido - Dominio Invalido")
                return 1
            
            KSR.registrar.save('location', 0)
            return 1

        if (msg.Method == "INVITE"):                      
            KSR.info("INVITE R-URI: " + KSR.pv.get("$ru") + "\n")
            KSR.info("        From: " + KSR.pv.get("$fu") +
                              " To:"+ KSR.pv.get("$tu") +"\n")
            if(KSR.pv.get("$fd") != "acme.pt" ): #verificar se o dominio e acme.pt
                KSR.info("Acesso negado- Fora do dominio acme.pt \n")
                KSR.sl.send_reply(403, "Proibido - Dominio Invalido")
                return 1
            
            if (KSR.pv.get("$td") == "acme.pt"):   # Check if To domain is a.pt   
                if (KSR.pv.get("$tu") == "sip:announce@a.pt"):  # Special To-URI tratar de maneira especial vamos usar para a conferencia
                    KSR.tm.t_on_reply("ksr_onreply_route_INVITE")
                    KSR.tm.t_on_failure("ksr_failure_route_INVITE")                 
                    KSR.pv.sets("$ru", "sip:announce@127.0.0.1:5090")
                    KSR.forward()       # Forwarding using statless mode
#                    KSR.tm.t_relay()    # Relaying using transaction mode
                    return 1  
                if (KSR.registrar.lookup("location") == 1):  # Check if registered
                    KSR.info("  lookup changed R-URI: " + KSR.pv.get("$ru") +"\n")
#                  KSR.rr.record_route()  # Add Record-Route header
                    KSR.tm.t_relay()
                else:
                    KSR.sl.send_reply(404, "Not found")
            else:
#               KSR.rr.record_route()
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
