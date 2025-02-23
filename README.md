# API Client

`ml_api_client` est une bibliothèque Python conçue pour faciliter l'interaction avec l'API de Mathis LAMBERT. Elle
utilise `aiohttp` pour gérer les requêtes HTTP de manière asynchrone, ce qui la rend idéale pour les applications
nécessitant des performances élevées et une gestion efficace des connexions simultanées.

## Fonctionnalités

- **Connexion asynchrone** : Utilise `aiohttp` pour des requêtes HTTP non bloquantes.
- **Facile à utiliser** : API simple et intuitive pour une intégration rapide dans vos projets.
- **Authentification sécurisée** : Supporte l'authentification par jeton et clé API.
- **Gestion des sessions** : Support des cookies et des en-têtes personnalisés.
- **Modèles Pydantic** : Utilisation de modèles Pydantic pour la validation et la gestion des données.

## Installation

Pour installer `ml_api_client`, utilisez pip :

```bash
pip install ml_api_client
```

## Utilisation

Voici un exemple de base pour utiliser `ml_api_client` dans votre projet :

```python
import asyncio
from ml_api_client import APIClient


async def main():
    # Initialisez le client avec l'URL de base de votre API
    client = APIClient(api_key="your_api_key")

    # Effectuez une requête de connexion asynchrone
    response = await client.auth.login(username="your_username", password="your_password")
    print(response)


# Exécutez la fonction principale
asyncio.run(main())
```

## Configuration

Vous pouvez configurer `APIClient` avec différentes options :

- `base_url` : L'URL de base de votre API.
- `api_key` : Clé API pour l'authentification.
- `headers` : En-têtes HTTP personnalisés.
- `timeout` : Délai d'attente pour les requêtes.

```python
client = APIClient(
    base_url="https://api.mathislambert.fr/v1",
    api_key="your_api_key",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    timeout=10
)
```

## Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Forkez le dépôt.
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/new-feature`).
3. Commitez vos modifications (`git commit -am 'Add new feature'`).
4. Poussez vers la branche (`git push origin feature/new-feature`).
5. Ouvrez une Pull Request.

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## Contact

Pour toute question ou suggestion, n'hésitez pas à ouvrir une issue ou à contacter l'auteur :

- **Mathis LAMBERT** : mathislambert.dev@gmail.com
