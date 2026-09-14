# Budget forecast — projection du 9 septembre 2026

Le scénario ci-dessous couvre un mois de 31 jours, sauvegardes et copies comprises. Il compte volontairement tout le web et PostgreSQL Development, faute d'attribution marginale fiable. Ce calcul est une projection conditionnelle, pas une facture mesurée ni une garantie de plafond.

Tarifs utilisés : [ressources Railway](https://docs.railway.com/pricing/plans) et [stockage objet](https://docs.railway.com/storage-buckets/billing). CPU : 0,000463 USD/vCPU/minute ; RAM : 0,000231 USD/Go/minute ; volume : 0,15 USD/Go/mois ; objets : 0,015 USD/Go/mois ; sortie réseau des services : 0,05 USD/Go. Quatre Gio valent 4,294967296 Go.

| Poste | Hypothèse mensuelle | USD |
| --- | --- | ---: |
| Jobs forecast | 31 × 5 min, 2 CPU / 4 Gio | 0,2973 |
| Sauvegardes | 31 × 5 min, mêmes ressources | 0,2973 |
| Essais et reprises supplémentaires | 10 × 5 min | 0,0959 |
| Cycle trimestriel entier | 3 candidats × 30 min | 0,1726 |
| Web et PostgreSQL complets | Moyenne cumulée 0,25 Go RAM | 2,5780 |
| Web et PostgreSQL complets | Moyenne cumulée 0,01 CPU | 0,2067 |
| Volume PostgreSQL | 1 Go | 0,1500 |
| Buckets, copies et historique | 2 Go au total | 0,0300 |
| Sortie réseau des services | 2 Go | 0,1000 |
| Sous-total | | 3,9278 |
| Provision de 20 % | | 0,7856 |
| Projection arrondie | | **4,72** |

L'heure observée comprend les redéploiements : moyenne cumulée RAM 0,2223 Go, CPU 0,002254 ; volume PostgreSQL maximal 0,1926 Go. Les buckets contiennent alors 336 901 octets primaires et 1 622 547 octets indépendants. Ces valeurs sont inférieures aux allocations du scénario. Une heure ne démontre pas une moyenne mensuelle ; les copies quotidiennes et les nouveaux candidats feront croître ces volumes.

Le worker synthétique exécuté dans Railway prend 4,92 secondes sous supervision, avec pic RSS 75 624 448 octets. Sa restauration logique prend 0,81 seconde. Le budget conserve pourtant les limites maximales par passage, et compte tout le cycle trimestriel le mois où il intervient. L'upload final du rapport de validation reste hors du chronométrage du superviseur, avec délais et reprises réseau bornés par le client S3.

Le relevé de facturation indique 1,471884 USD pour le projet complet, sur la période du 21 août au 21 septembre. Il est retardé, contient aussi la production et ne correspond pas au mois civil utilisé par les jobs. Ce nombre n'est donc pas injecté comme un coût forecast mensuel exact. Les relevés détaillés restent dans `%TEMP%/bitcoin-forecast-finish-20260909/usage.json` ; le modèle n'étant pas admissible, les nouveaux calculs réels restent désactivés.

## Conditions de validité

Recalculer la projection si la moyenne quotidienne web/PostgreSQL dépasse 0,25 Go RAM ou 0,01 CPU, si les allocations de stockage/transfert sont dépassées, ou après plus de dix essais supplémentaires. Avec les autres postes constants, une moyenne RAM cumulée de 0,2732 Go porterait déjà ce scénario à cinq USD. Ne pas attendre dix USD pour agir.

Le contrôle logiciel refuse les nouveaux calculs dès cinq USD mesurés ou projetés, ainsi qu'un relevé absent, périmé ou invalide. Le test cloud vérifie les deux seuils. Il ne transforme pas les réserves ci-dessus en limites imposées par Railway. Les sauvegardes continuent à protéger les données lorsque les calculs sont suspendus ; leur coût reste à comptabiliser. Le site et PostgreSQL ne sont pas arrêtés.

Avant activation d'un vrai modèle, fournir le relevé du mois civil courant, recalculé avec les artefacts réels et les mesures actualisées. Aucun zéro par défaut n'est utilisé pour autoriser une exécution réelle. Les données synthétiques du test gardent explicitement leur statut de fixture.
