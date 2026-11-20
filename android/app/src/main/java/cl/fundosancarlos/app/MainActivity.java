package cl.fundosancarlos.app;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.text.InputType;
import android.text.method.PasswordTransformationMethod;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.widget.*;
import com.google.firebase.messaging.FirebaseMessaging;
import org.json.JSONArray;
import org.json.JSONObject;
import java.text.NumberFormat;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final int GREEN=0xFF173D32, INK=0xFF23332D, MUTED=0xFF53675F, BG=0xFFF4F6F2,
        BLUE=0xFF1C73B0, AMBER=0xFFAC6808, RED=0xFFAA382F, WHITE=0xFFFFFFFF, LINE=0xFFE0E8E1;
    private static final int PERMISSION=37;
    private static final long REFRESH_INTERVAL_MS = 2_000;
    private final Handler clock=new Handler(Looper.getMainLooper());
    private final ExecutorService network=Executors.newSingleThreadExecutor();
    private LocalStore store;
    private LinearLayout frame, page;
    private ScrollView scroll;
    private TextView notice;
    private EditText thresholdField, readingField;
    private Spinner tankPicker;
    private JSONObject data;
    private String tab="inicio";
    private String liveToken="", liveOrigin="";
    private boolean busy, foreground, online, firebaseReady, returningFromSettings, pushLinkAttempted;
    private final NumberFormat number=NumberFormat.getNumberInstance(Locale.forLanguageTag("es-CL"));
    private final Runnable refreshLoop=new Runnable() {
        @Override public void run() {
            if (!foreground) return;
            if (!busy && !liveToken.isEmpty() && (tab.equals("inicio") || tab.equals("agua"))) refresh(false);
            clock.postDelayed(this, REFRESH_INTERVAL_MS);
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        getWindow().setStatusBarColor(GREEN);
        getWindow().setNavigationBarColor(GREEN);
        store=new LocalStore(this);
        number.setMaximumFractionDigits(2);
        PushAndroid.createChannel(this);
        try { firebaseReady=PushAndroid.configure(this); } catch (RuntimeException ignored) { firebaseReady=false; }
        liveOrigin=store.origin();
        liveToken=store.token();
        if (!BuildConfig.SERVER_URL.isEmpty() && !BuildConfig.SERVER_URL.equals(liveOrigin) && !liveToken.isEmpty()) {
            store.clearSession();
            liveToken="";
        }
        if ("agua".equals(getIntent().getStringExtra("pantalla"))) tab="agua";
        if (liveToken.isEmpty()) showLogin();
        else {
            data=store.cachedPanel();
            render();
            refresh(true);
        }
    }

    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (!liveToken.isEmpty()) { tab="agua"; render(); refresh(true); }
    }
    @Override protected void onResume() {
        super.onResume();
        foreground=true;
        clock.removeCallbacks(refreshLoop);
        clock.postDelayed(refreshLoop, REFRESH_INTERVAL_MS);
        if (returningFromSettings) {
            returningFromSettings=false;
            if (PushAndroid.allowed(this)) vincular();
            else setNotice("Los avisos siguen desactivados en este teléfono.",false);
        } else if (!busy && !liveToken.isEmpty()) {
            refresh(false);
            if (store.wantsPush() && firebaseReady && PushAndroid.allowed(this)) sincronizarToken();
        }
    }
    @Override protected void onPostResume() {
        super.onPostResume();
        if (Build.VERSION.SDK_INT >= 33 && !PushAndroid.allowed(this)
                && !getPreferences(MODE_PRIVATE).getBoolean("pedido", false)) {
            getPreferences(MODE_PRIVATE).edit().putBoolean("pedido", true).apply();
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, PERMISSION);
        }
    }
    @Override protected void onPause() {
        foreground=false;
        clock.removeCallbacks(refreshLoop);
        super.onPause();
    }
    @Override protected void onDestroy() {
        clock.removeCallbacksAndMessages(null);
        network.shutdown();
        store.close();
        super.onDestroy();
    }

    private int dp(float n) { return (int)(getResources().getDisplayMetrics().density*n+.5f); }
    private GradientDrawable bg(int color, int radius) {
        GradientDrawable d=new GradientDrawable();
        d.setColor(color); d.setCornerRadius(dp(radius)); return d;
    }
    private LinearLayout column() {
        LinearLayout v=new LinearLayout(this); v.setOrientation(LinearLayout.VERTICAL); return v;
    }
    private LinearLayout row() {
        LinearLayout v=new LinearLayout(this); v.setOrientation(LinearLayout.HORIZONTAL); v.setGravity(Gravity.CENTER_VERTICAL); return v;
    }
    private TextView text(String value, int size, int color, boolean bold) {
        TextView v=new TextView(this);
        v.setText(value); v.setTextSize(size); v.setTextColor(color); v.setLineSpacing(dp(2),1f);
        if (bold) v.setTypeface(null,Typeface.BOLD);
        return v;
    }
    private void gap(LinearLayout parent, int height) {
        parent.addView(new View(this),new LinearLayout.LayoutParams(1,dp(height)));
    }
    private Button button(String title, boolean primary, View.OnClickListener click) {
        Button b=new Button(this); b.setText(title); b.setTextSize(15); b.setAllCaps(false);
        b.setTextColor(primary?WHITE:GREEN);
        b.setBackground(bg(primary?GREEN:0xFFE7F0EB,12));
        b.setMinHeight(dp(52)); b.setPadding(dp(14),dp(10),dp(14),dp(10));
        b.setOnClickListener(click);
        return b;
    }
    private void putButton(LinearLayout parent, String label, boolean primary, View.OnClickListener listener) {
        gap(parent,12); parent.addView(button(label,primary,listener),new LinearLayout.LayoutParams(-1,-2));
    }
    private LinearLayout card() {
        LinearLayout c=column(); c.setPadding(dp(18),dp(16),dp(18),dp(16)); c.setBackground(bg(WHITE,18));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2); lp.bottomMargin=dp(14);
        page.addView(c,lp); return c;
    }
    private EditText input(LinearLayout parent, String label, String value, int type) {
        gap(parent,10);
        TextView caption=text(label,14,INK,true); parent.addView(caption);
        EditText field=new EditText(this);
        field.setId(View.generateViewId()); caption.setLabelFor(field.getId());
        field.setInputType(type); field.setSingleLine(true); field.setText(value); field.setTextColor(INK); field.setTextSize(16);
        field.setPadding(dp(12),dp(10),dp(12),dp(10)); field.setMinHeight(dp(52)); field.setBackground(bg(BG,10));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2); lp.topMargin=dp(5);
        parent.addView(field,lp); return field;
    }
    private void shell(boolean login) {
        frame=column(); frame.setBackgroundColor(BG);
        frame.setOnApplyWindowInsetsListener((v,insets)->{
            if (Build.VERSION.SDK_INT >= 30) {
                var sys=insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                var ime=insets.getInsets(WindowInsets.Type.ime());
                v.setPadding(sys.left,sys.top,sys.right,Math.max(sys.bottom,ime.bottom));
            } else v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),
                                insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets;
        });
        LinearLayout header=column(); header.setBackgroundColor(GREEN);
        header.setPadding(dp(22),dp(18),dp(22),dp(17));
        header.addView(text("FUNDO SAN CARLOS",12,0xFFC0DFD2,true));
        header.addView(text(login?"Control de recursos":headerTitle(),25,WHITE,true));
        if (!login && data!=null) {
            header.addView(text(data.optString("nombre")+" · "+(admin()?"Administrador":"Trabajador"),13,0xFFD3E6DC,false));
        }
        frame.addView(header);
        scroll=new ScrollView(this); scroll.setFillViewport(true);
        page=column(); page.setPadding(dp(18),dp(18),dp(18),dp(22));
        scroll.addView(page,new ScrollView.LayoutParams(-1,-2));
        frame.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        notice=text("",14,MUTED,false); notice.setVisibility(View.GONE); notice.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        page.addView(notice);
        if (!login) {
            LinearLayout nav=row(); nav.setPadding(dp(8),dp(7),dp(8),dp(7)); nav.setBackgroundColor(WHITE);
            tabButton(nav,"Inicio","inicio"); tabButton(nav,"Agua","agua");
            if(admin()) tabButton(nav,"Alertas","alertas");
            tabButton(nav,"Cuenta","cuenta"); frame.addView(nav);
        }
        setContentView(frame);
        frame.requestApplyInsets();
    }
    private String headerTitle() {
        return switch (tab) {
            case "agua" -> "Monitoreo de agua";
            case "alertas" -> "Alertas de agua";
            case "lectura" -> "Registro de lecturas";
            case "cuenta" -> "Mi cuenta";
            default -> "Vista general";
        };
    }
    private void tabButton(LinearLayout nav, String label, String target) {
        Button b=button(label,tab.equals(target),v->{ if(!busy){tab=target;render();if(target.equals("agua")||target.equals("inicio")||target.equals("alertas")) refresh(false);} });
        b.setTextSize(13); b.setPadding(dp(4),dp(7),dp(4),dp(7));
        LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(0,-2,1); params.setMargins(dp(3),0,dp(3),0);
        nav.addView(b,params);
    }
    private void setNotice(String message, boolean good) {
        if(notice==null)return;
        notice.setVisibility(message.isEmpty()?View.GONE:View.VISIBLE);
        notice.setText(message);
        notice.setTextColor(good?GREEN:RED);
        notice.setPadding(dp(10),dp(9),dp(10),dp(9));
    }
    private void showLogin() {
        shell(true);
        LinearLayout c=card();
        c.addView(text("Iniciar sesión",24,INK,true));
        c.addView(text("Ingresa con la misma cuenta que usas en la web.",15,MUTED,false));
        final String defaultAddress = !BuildConfig.SERVER_URL.isEmpty() ? BuildConfig.SERVER_URL
            : BuildConfig.DEBUG ? "http://127.0.0.1:8000" : "";
        EditText origin = null;
        if (BuildConfig.DEBUG && BuildConfig.SERVER_URL.isEmpty()) {
            LinearLayout advanced = column();
            advanced.setVisibility(View.GONE);
            putButton(c,"Opciones de conexión",false,v ->
                advanced.setVisibility(advanced.getVisibility()==View.VISIBLE ? View.GONE : View.VISIBLE));
            c.addView(advanced);
            origin=input(advanced,"Servidor de prueba",defaultAddress,InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_URI);
            origin.setHint("http://127.0.0.1:8000");
        }
        final EditText optionalOrigin = origin;
        EditText user=input(c,"Usuario","",InputType.TYPE_CLASS_TEXT);
        EditText password=input(c,"Contraseña","",InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
        // La entrada debe permanecer oculta incluso si setSingleLine modifica el tipo del campo.
        password.setTransformationMethod(PasswordTransformationMethod.getInstance());
        password.setAutofillHints(View.AUTOFILL_HINT_PASSWORD);
        user.setAutofillHints(View.AUTOFILL_HINT_USERNAME);
        password.setSaveEnabled(false);
        putButton(c,"Ingresar",true,v->{
            if(busy)return;
            final String address;
            if (defaultAddress.isEmpty() && optionalOrigin == null) {
                setNotice("Esta versión no tiene un servidor configurado.",false); return;
            }
            try {address=Api.origin(optionalOrigin==null ? defaultAddress : optionalOrigin.getText().toString());}
            catch(IllegalArgumentException e){setNotice(e.getMessage(),false);return;}
            String username=user.getText().toString().trim(), secret=password.getText().toString();
            if(username.isEmpty()||secret.isEmpty()){setNotice("Ingresa usuario y contraseña.",false);return;}
            call("Conectando con San Carlos…",()-> {
                JSONObject result=Api.request(address,"ingresar","",new JSONObject().put("usuario",username).put("contrasena",secret));
                store.saveSession(address,result.getString("usuario"),result.getString("token"));
                return result;
            },result->{
                password.setText("");
                liveOrigin=address;liveToken=result.optString("token");data=null;tab="inicio";online=false;pushLinkAttempted=false;
                render();refresh(true);
            },false);
        });
    }
    private boolean admin(){return data!=null && "administrador".equals(data.optString("rol"));}
    private JSONArray list(String name){
        JSONArray result=data==null?null:data.optJSONArray(name);
        return result==null?new JSONArray():result;
    }
    private JSONObject water(){
        JSONArray tanks=list("estanques");
        for(int i=0;i<tanks.length();i++){
            JSONObject tank=tanks.optJSONObject(i);
            if(tank!=null&&"agua".equals(tank.optString("tipo")))return tank;
        }
        return new JSONObject();
    }
    private void render(){
        if(liveToken.isEmpty()){showLogin();return;}
        if(!admin() && (tab.equals("alertas")||tab.equals("lectura"))) tab="inicio";
        shell(false);
        if(!online && data!=null) setNotice("Sin conexión · mostrando los últimos datos guardados",false);
        if(data==null && !tab.equals("cuenta")){
            LinearLayout c=card();
            c.addView(text("Aún no hay datos disponibles.",17,INK,true));
            putButton(c,"Actualizar niveles",true,v->refresh(true));
            return;
        }
        switch(tab){
            case "alertas" -> alerts();
            case "lectura" -> reading();
            case "cuenta" -> account();
            default -> dashboard();
        }
    }
    private void dashboard(){
        boolean onlyWater=tab.equals("agua");
        JSONArray tanks=list("estanques");
        for(int i=0;i<tanks.length();i++){
            JSONObject tank=tanks.optJSONObject(i);
            if(tank==null||(onlyWater&&!"agua".equals(tank.optString("tipo"))))continue;
            tankCard(tank);
        }
        if(tanks.length()==0)card().addView(text("No hay estanques configurados.",17,INK,true));
        LinearLayout actions=card();
        putButton(actions,"Actualizar niveles",false,v->refresh(true));
        if(admin()){
            putButton(actions,"Configurar alertas de agua",true,v->{tab="alertas";render();});
            putButton(actions,"Registro de lecturas",false,v->{tab="lectura";render();});
            if(list("lecturas").length()>0) {
                LinearLayout log=card(); log.addView(text("Últimas lecturas",19,INK,true));
                JSONArray readings=list("lecturas");
                for(int i=0;i<readings.length();i++){
                    JSONObject m=readings.optJSONObject(i);
                    if(m==null||(onlyWater&&!"agua".equals(m.optString("tipo"))))continue;
                    gap(log,9);log.addView(text(m.optString("estanque")+" · "+formatVolume("agua".equals(m.optString("tipo")) ? water() : null, m.optDouble("litros",0)),14,INK,true));
                    log.addView(text(date(m.optString("fecha"))+(m.optBoolean("simulada")?" · Simulada":""),12,MUTED,false));
                }
            }
        }
    }
    private String formatVolume(JSONObject tank, double liters) {
        String unit = tank == null ? "" : tank.optString("unidad_volumen");
        boolean milliliters = "mL".equals(unit) || (tank != null && unit.isEmpty()
            && "agua".equals(tank.optString("tipo")) && tank.optDouble("capacidad", 2) <= 1);
        return milliliters ? number.format(Math.round(liters * 1000)) + " mL" : number.format(liters) + " L";
    }

    private void tankCard(JSONObject t){
        boolean water="agua".equals(t.optString("tipo"));
        boolean missing=t.isNull("porcentaje");
        boolean stale=!online||t.optBoolean("desactualizado");
        boolean low=!stale&&t.optBoolean("bajo");
        int accent=water?BLUE:AMBER;
        LinearLayout c=card();
        c.addView(text(water?"SUMINISTRO HÍDRICO":"COMBUSTIBLE",11,accent,true));
        c.addView(text(t.optString("nombre"),21,INK,true));
        gap(c,13);
        LinearLayout body=row(); c.addView(body);
        double pct=t.optDouble("porcentaje",0);
        Gauge gauge=new Gauge(this,missing?-1:pct,accent);
        body.addView(gauge,new LinearLayout.LayoutParams(dp(104),dp(104)));
        LinearLayout amounts=column(); amounts.setPadding(dp(14),0,0,0);
        body.addView(amounts,new LinearLayout.LayoutParams(0,-2,1));
        amounts.addView(text(missing?"—":formatVolume(t, t.optDouble("volumen",0)),23,INK,true));
        amounts.addView(text("Capacidad: "+formatVolume(t, t.optDouble("capacidad",0)),13,MUTED,false));
        String state=missing?"Sin mediciones":stale?"Datos desactualizados":low?"Nivel bajo":water?"Nivel normal":"Nivel disponible";
        amounts.addView(text(state,14,low?RED:stale?AMBER:GREEN,true));
        gap(c,12);
        c.addView(text(missing?"Esperando primera lectura":"Última lectura: "+date(t.optString("fecha"))+
                (t.optBoolean("simulada")?" · Simulada":""),12,MUTED,false));
        if(water&&admin()&&!t.isNull("umbral"))c.addView(text("Umbral de alerta: "+number.format(t.optDouble("umbral"))+" %",13,INK,true));
    }
    private void alerts(){
        LinearLayout c=card();
        c.addView(text("Nivel mínimo de agua",21,INK,true));
        c.addView(text("Recibirás un aviso cuando el nivel baje de este porcentaje.",14,MUTED,false));
        thresholdField=input(c,"Umbral (%)",number.format(water().optDouble("umbral",30)),InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL);
        Button save=button("Guardar umbral",true,v->{
            String pct=percent(thresholdField);
            if(pct!=null) call("Guardando umbral…",()->{
                Api.request(liveOrigin,"umbral",liveToken,new JSONObject().put("porcentaje",pct));
                return Api.request(liveOrigin,"panel",liveToken,null);
            },r->{updatePanel(r);render();setNotice("Umbral guardado.",true);},true);
        });
        gap(c,12);c.addView(save);
        LinearLayout n=card();n.addView(text("Notificaciones al teléfono",20,INK,true));
        boolean server=data.optBoolean("notificaciones_disponibles");
        boolean linked=data.optBoolean("notificaciones_vinculadas")&&PushAndroid.allowed(this);
        n.addView(text(linked?"Avisos activados en este teléfono.":(!firebaseReady||!server)
            ?"El envío de avisos aún no está disponible.":"Activa los avisos de San Carlos para recibir alertas con el teléfono bloqueado.",14,MUTED,false));
        if(firebaseReady&&server) {
            putButton(n,linked?"Revisar permiso de avisos":"Activar notificaciones",true,v->{
                if(linked) openNotificationSettings();
                else requestNotifications();
            });
            if(data.optBoolean("notificaciones_vinculadas")) putButton(n,"Desactivar en este teléfono",false,v->
                call("Desactivando avisos…",()->{
                    Api.request(liveOrigin,"notificaciones",liveToken,new JSONObject().put("accion","quitar"));
                    store.wantsPush(false);
                    store.automaticPushAllowed(false);
                    return Api.request(liveOrigin,"panel",liveToken,null);
                },r->{updatePanel(r);render();setNotice("Avisos desactivados.",true);},true));
        }
        LinearLayout history=card();history.addView(text("Historial de alertas",19,INK,true));
        JSONArray alerts=list("alertas");
        if(alerts.length()==0) history.addView(text("No hay alertas registradas.",14,MUTED,false));
        for(int i=0;i<alerts.length();i++){
            JSONObject a=alerts.optJSONObject(i);if(a==null)continue;
            gap(history,12);
            boolean resolved=a.optBoolean("resuelta");
            history.addView(text(resolved?"Resuelta":"Nivel bajo · Activa",15,resolved?GREEN:RED,true));
            history.addView(text(date(a.optString("fecha"))+" · "+formatVolume(water(), a.optDouble("litros")),13,MUTED,false));
        }
    }
    private void reading(){
        LinearLayout c=card();
        c.addView(text("Registrar nivel",21,INK,true));
        c.addView(text("Selecciona el estanque e ingresa el porcentaje observado.",14,MUTED,false));
        gap(c,12);
        tankPicker=new Spinner(this);
        tankPicker.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"Estanque de agua","Estanque de petróleo"}));
        tankPicker.setMinimumHeight(dp(48));tankPicker.setContentDescription("Estanque");
        c.addView(tankPicker);
        readingField=input(c,"Nivel (%)","",InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL);
        putButton(c,"Guardar lectura",true,v->{
            String pct=percent(readingField);if(pct==null)return;
            String type=tankPicker.getSelectedItemPosition()==0?"agua":"petroleo";
            call("Guardando lectura…",()->{
                Api.request(liveOrigin,"lectura",liveToken,new JSONObject().put("tipo",type).put("porcentaje",pct));
                return Api.request(liveOrigin,"panel",liveToken,null);
            },r->{updatePanel(r);tab="inicio";render();setNotice("Lectura guardada.",true);},true);
        });
        putButton(c,"Volver al panel",false,v->{if(!busy){tab="inicio";render();}});
    }
    private void account(){
        LinearLayout c=card();
        c.addView(text(store.user(),20,INK,true));
        c.addView(text(BuildConfig.DEBUG?"Servidor: "+liveOrigin:"Conexión de San Carlos",14,MUTED,false));
        putButton(c,"Cerrar sesión",true,v->{
            if(busy)return;
            String origin=liveOrigin, token=liveToken;
            call("Cerrando sesión…",()->Api.request(origin,"salir",token,new JSONObject()),
                r->clearSession("Sesión cerrada."),true);
        });
        if (BuildConfig.DEBUG && BuildConfig.SERVER_URL.isEmpty()) {
            putButton(c,"Volver a configurar conexión",false,v->new AlertDialog.Builder(this)
                .setTitle("Cambiar conexión")
                .setMessage("Se cerrará la sesión local. Usa esta opción si el servidor de prueba anterior ya no está disponible.")
                .setNegativeButton("Cancelar",null)
                .setPositiveButton("Continuar",(dialog,which)->{
                    if (busy) return;
                    if (store.wantsPush() && firebaseReady) FirebaseMessaging.getInstance().deleteToken();
                    clearSession("Ingresa nuevamente para conectar.");
                }).show());
        }
    }
    private String percent(EditText field){
        try{
            var decimal=new java.math.BigDecimal(field.getText().toString().trim().replace(',','.'));
            if(decimal.signum()<0||decimal.compareTo(new java.math.BigDecimal(100))>0||decimal.scale()>2)throw new IllegalArgumentException();
            return decimal.toPlainString();
        }catch(RuntimeException e){field.setError("Ingresa un número entre 0 y 100 con hasta dos decimales.");return null;}
    }
    private String date(String raw){
        try{return OffsetDateTime.parse(raw).atZoneSameInstant(ZoneId.of("America/Santiago"))
            .format(DateTimeFormatter.ofPattern("dd/MM HH:mm",Locale.forLanguageTag("es-CL")));}
        catch(RuntimeException e){return "Sin fecha";}
    }
    private void clearSession(String message){
        store.clearSession();liveToken="";data=null;online=false;tab="inicio";showLogin();setNotice(message,true);
    }
    private void updatePanel(JSONObject r){data=r;online=true;store.savePanel(r);}
    private void refresh(boolean visible){
        if(busy||liveToken.isEmpty())return;
        int y=scroll==null?0:scroll.getScrollY();
        call(visible?"Actualizando niveles…":"",()->Api.request(liveOrigin,"panel",liveToken,null),r->{
            updatePanel(r);
            if(!tab.equals("lectura")&&(visible||!tab.equals("alertas"))){
                render();scroll.post(()->scroll.scrollTo(0,y));
            }
            linkAfterLogin();
        },true);
    }
    private interface Task {JSONObject run() throws Exception;}
    private interface Done {void run(JSONObject result);}
    private void call(String working, Task task, Done done, boolean authenticated){
        if(busy)return;
        busy=true;
        if(!working.isEmpty())setNotice(working,true);
        network.execute(()->{
            try{
                JSONObject result=task.run();
                runOnUiThread(()->{busy=false;if(!isDestroyed())done.run(result);});
            }catch(Exception error){
                runOnUiThread(()->{
                    busy=false;if(isDestroyed())return;
                    if(authenticated&&error instanceof Api.Error e&&e.status==401){
                        clearSession("La sesión expiró. Vuelve a ingresar.");return;
                    }
                    if(error instanceof Api.Error) setNotice(error.getMessage(),false);
                    else {
                        online=false;
                        if(authenticated&&(tab.equals("inicio")||tab.equals("agua")))render();
                        setNotice(data!=null?"No se pudo conectar. Se muestran los últimos datos guardados."
                            :"No se pudo conectar. Comprueba la dirección, la red y que Django esté iniciado.",false);
                    }
                });
            }
        });
    }
    private void requestNotifications(){
        if(!firebaseReady||busy)return;
        if(PushAndroid.allowed(this)){vincular();return;}
        if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED
            && !getPreferences(MODE_PRIVATE).getBoolean("pedido",false)){
            getPreferences(MODE_PRIVATE).edit().putBoolean("pedido",true).apply();
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},PERMISSION);
        }else openNotificationSettings();
    }
    @Override public void onRequestPermissionsResult(int code,String[] permissions,int[] result){
        super.onRequestPermissionsResult(code,permissions,result);
        if(code==PERMISSION){
            if(result.length>0&&result[0]==PackageManager.PERMISSION_GRANTED)linkAfterLogin();
            else if(admin()) setNotice("Puedes habilitar los avisos más tarde desde Alertas.",false);
        }
    }
    private void openNotificationSettings(){
        Intent settings=new Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
            .putExtra(Settings.EXTRA_APP_PACKAGE,getPackageName());
        returningFromSettings=true;
        startActivity(settings);
    }
    private void linkAfterLogin(){
        if (!pushLinkAttempted && !busy && admin() && firebaseReady && PushAndroid.allowed(this)
                && store.automaticPushAllowed() && data.optBoolean("notificaciones_disponibles")
                && !data.optBoolean("notificaciones_vinculadas")) {
            pushLinkAttempted=true;
            vincular(true);
        }
    }
    private void vincular(){vincular(false);}
    private void vincular(boolean automatic){
        if(!firebaseReady||liveToken.isEmpty()||!admin())return;
        if(!automatic) setNotice("Vinculando el teléfono…",true);
        final String session=liveToken;
        FirebaseMessaging.getInstance().getToken().addOnCompleteListener(task->{
            if(isDestroyed()||!session.equals(liveToken))return;
            if(!task.isSuccessful()){if(!automatic)setNotice("No se pudo vincular. Revisa internet y los servicios de Google Play.",false);return;}
            String fcm=task.getResult();
            call(automatic?"":"Guardando la suscripción…",()->{
                Api.request(liveOrigin,"notificaciones",session,new JSONObject().put("token",fcm));
                store.wantsPush(true);
                store.automaticPushAllowed(true);
                return Api.request(liveOrigin,"panel",session,null);
            },r->{updatePanel(r);render();setNotice("Notificaciones activadas en este teléfono.",true);},true);
        });
    }
    private void sincronizarToken(){
        final String session=liveToken, address=liveOrigin;
        FirebaseMessaging.getInstance().getToken().addOnSuccessListener(token->{
            if(isDestroyed()||!session.equals(liveToken)||!store.wantsPush())return;
            network.execute(()->{
                try {Api.request(address,"notificaciones",session,new JSONObject().put("token",token));}
                catch(Exception ignored){}
            });
        });
    }

    private static final class Gauge extends View{
        final double pct; final int color; final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
        Gauge(Activity a,double p,int c){super(a);pct=p;color=c;setContentDescription(p<0?"Sin medición":Math.round(p)+" por ciento");}
        @Override protected void onDraw(Canvas canvas){
            super.onDraw(canvas);
            float size=Math.min(getWidth(),getHeight()), mid=size/2f, pad=size*.08f;
            RectF box=new RectF(pad,pad,size-pad,size-pad);
            paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(size*.08f);paint.setColor(LINE);
            canvas.drawArc(box,0,360,false,paint);
            if(pct>=0){paint.setColor(color);canvas.drawArc(box,-90,(float)(Math.max(0,Math.min(100,pct))*3.6),false,paint);}
            paint.setStyle(Paint.Style.FILL);paint.setColor(INK);paint.setTextAlign(Paint.Align.CENTER);
            paint.setTypeface(Typeface.DEFAULT_BOLD);paint.setTextSize(size*.23f);
            canvas.drawText(pct<0?"—":Math.round(pct)+" %",mid,mid-(paint.ascent()+paint.descent())/2,paint);
        }
    }
}
