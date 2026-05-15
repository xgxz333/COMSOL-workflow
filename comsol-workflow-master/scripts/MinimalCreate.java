public class MinimalCreate {
  public static void main(String[] args) {
    try {
      com.comsol.model.util.ModelUtil.initStandalone(false);
      com.comsol.model.util.ModelUtil.loadPreferences();
      System.out.println("before_create");
      com.comsol.model.Model model = com.comsol.model.util.ModelUtil.create("Model1");
      System.out.println("after_create: " + model);
    } catch (Throwable t) {
      t.printStackTrace();
      System.exit(2);
    }
  }
}
