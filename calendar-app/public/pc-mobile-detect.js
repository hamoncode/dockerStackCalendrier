document.addEventListener("DOMContentLoaded", ()=>{
    //Détecter si l'appareil est sur mobile
    let mobile = false;
    if (navigator.userAgent.indexOf("Android") != -1 || navigator.userAgent.indexOf("like Mac") != -1){
        mobile = true;
    }

    let domain = location.protocol+"//"+location.hostname+":"+location.port;
    if (mobile && location.pathname.indexOf("mobile") == -1){
        location.replace(domain+"/mobile/calendrier.html");
    }else if(!mobile && location.pathname.indexOf("pc") == -1){
        location.replace(domain+"/pc/calendrier.html");
    }
});