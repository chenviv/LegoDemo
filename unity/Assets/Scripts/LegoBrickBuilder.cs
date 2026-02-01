using UnityEngine;

public class LegoBrickBuilder : MonoBehaviour
{
    [Header("LEGO Dimensions")]
    public int studsWidth = 2;
    public int studsLength = 4;
    public float brickHeight = 0.96f; // Standard LEGO brick height in Unity units
    
    [Header("Materials")]
    public Material brickMaterial;
    
    private const float STUD_SPACING = 0.8f; // Standard LEGO stud spacing
    private const float STUD_HEIGHT = 0.18f;
    private const float STUD_RADIUS = 0.24f;
    
    void Start()
    {
        if (brickMaterial == null)
        {
            // Create default red material with fallback shader
            Shader shader = Shader.Find("Standard");
            if (shader == null)
            {
                shader = Shader.Find("Unlit/Color");
            }
            if (shader == null)
            {
                shader = Shader.Find("Diffuse");
            }
            
            if (shader != null)
            {
                brickMaterial = new Material(shader);
                brickMaterial.color = new Color(0.8f, 0.1f, 0.1f); // LEGO red
            }
            else
            {
                Debug.LogError("Could not find any shader for LEGO brick material!");
            }
        }
        
        BuildLegoBrick();
    }
    
    void BuildLegoBrick()
    {
        // Create main brick body
        GameObject brickBody = CreateBrickBody();
        
        // Create studs on top
        CreateStuds();
        
        // Center the brick at origin
        transform.position = Vector3.zero;
    }
    
    GameObject CreateBrickBody()
    {
        GameObject body = GameObject.CreatePrimitive(PrimitiveType.Cube);
        body.name = "BrickBody";
        body.transform.SetParent(transform);
        body.transform.localPosition = Vector3.zero;
        
        // Calculate dimensions
        float width = studsWidth * STUD_SPACING;
        float length = studsLength * STUD_SPACING;
        
        body.transform.localScale = new Vector3(width, brickHeight, length);
        body.GetComponent<Renderer>().material = brickMaterial;
        
        return body;
    }
    
    void CreateStuds()
    {
        float width = studsWidth * STUD_SPACING;
        float length = studsLength * STUD_SPACING;
        
        // Calculate starting position for studs
        float startX = -(studsWidth - 1) * STUD_SPACING / 2f;
        float startZ = -(studsLength - 1) * STUD_SPACING / 2f;
        float studY = brickHeight / 2f + STUD_HEIGHT / 2f;
        
        for (int x = 0; x < studsWidth; x++)
        {
            for (int z = 0; z < studsLength; z++)
            {
                GameObject stud = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                stud.name = $"Stud_{x}_{z}";
                stud.transform.SetParent(transform);
                
                // Position stud
                float posX = startX + x * STUD_SPACING;
                float posZ = startZ + z * STUD_SPACING;
                stud.transform.localPosition = new Vector3(posX, studY, posZ);
                
                // Scale stud
                stud.transform.localScale = new Vector3(
                    STUD_RADIUS * 2, 
                    STUD_HEIGHT, 
                    STUD_RADIUS * 2
                );
                
                stud.GetComponent<Renderer>().material = brickMaterial;
            }
        }
    }
}
