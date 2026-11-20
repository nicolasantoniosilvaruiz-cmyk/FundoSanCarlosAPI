package cl.fundosancarlos.app;

import android.app.Application;

public final class SanCarlosApplication extends Application {
    @Override public void onCreate() {
        super.onCreate();
        PushAndroid.createChannel(this);
        // Se ejecuta también cuando Android inicia el proceso para entregar un aviso.
        try { PushAndroid.configure(this); } catch (RuntimeException ignored) {}
    }
}
