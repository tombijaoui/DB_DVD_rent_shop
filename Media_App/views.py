from django.shortcuts import render
from django.db import connection

from Media_App.models import Recordorders, Households, Programs, Recordreturns, Programranks


def index(request):
    return render(request, 'index.html')


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def queryResult(request):
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT MaxDurationGenre.genre, MIN(DISTINCT P2.title) AS title, MaxDurationGenre.maxDuration
FROM(SELECT MorethanOne.genre, MAX(DISTINCT MoreThanOne.duration) AS maxDuration
     FROM(SELECT WithoutKidsPrograms.genre, WithoutKidsPrograms.duration
          FROM(SELECT GenreAndDuration.genre, GenreAndDuration.title, GenreAndDuration.duration, GenreAndDuration.hID
               FROM(SELECT P1.genre, RR1.title, P1.duration, RR1.hID
                    FROM RecordReturns RR1
                    LEFT JOIN Programs P1 ON RR1.title = P1.title
                    WHERE P1.genre LIKE 'A%') AS GenreAndDuration
               LEFT JOIN Households H1 ON H1.hID = GenreAndDuration.hID
               WHERE H1.ChildrenNum = 0) AS WithoutKidsPrograms
          GROUP BY WithoutKidsPrograms.genre, WithoutKidsPrograms.title, WithoutKidsPrograms.duration
          HAVING COUNT(DISTINCT WithoutKidsPrograms.hID) >= 1) AS MoreThanOne
     GROUP BY MorethanOne.genre) AS MaxDurationGenre
LEFT JOIN Programs P2 ON P2.genre = MaxDurationGenre.genre AND P2.duration = MaxDurationGenre.maxDuration
GROUP BY MaxDurationGenre.genre, MaxDurationGenre.maxDuration
ORDER BY MaxDurationGenre.genre
        """)
        sql_res1 = dictfetchall(cursor)

        cursor.execute("""
        SELECT KosherPrograms.title, CAST(AVG(CAST(PR2.rank AS DECIMAL(10,2))) AS DECIMAL(10,2)) AS Average_Rank
FROM (SELECT AllRecords.title
      FROM(SELECT *
           FROM RecordOrders RO1
           UNION
           SELECT *
           FROM RecordReturns RR1) AS AllRecords
      INNER JOIN ProgramRanks PR1 ON AllRecords.title = PR1.title AND AllRecords.hID = PR1.hID
      GROUP BY AllRecords.title
      HAVING COUNT(DISTINCT AllRecords.hID) >= 3) AS KosherPrograms
LEFT JOIN ProgramRanks PR2 ON KosherPrograms.title = PR2.title
GROUP BY KosherPrograms.title
ORDER BY Average_Rank DESC, KosherPrograms.title
        """)
        sql_res2 = dictfetchall(cursor)

        cursor.execute("""
        SELECT QualitativeProgramsWithNumBadGrade.title
FROM (SELECT QualitativePrograms.title, COUNT(IIF(PR1.rank < 2, 1, NULL)) AS Num_Bad_Grade
      FROM(SELECT WealthyFamiliesbyProgram.title
           FROM(SELECT ProgramsWithNetWorth.title, ProgramsWithNetWorth.Number_Return_Families, COUNT(ProgramsWithNetWorth.hID) AS Wealthy_Families
                FROM(SELECT ProgramsWithNumberFamiliesAndFamilies.title, ProgramsWithNumberFamiliesAndFamilies.Number_Return_Families,
                        H1.hID
                     FROM(SELECT ProgramsWithNumberFamilies.title, ProgramsWithNumberFamilies.Number_Return_Families, RR2.hID
                        FROM (SELECT RR1.title, COUNT(DISTINCT RR1.hID) AS Number_Return_Families
                              FROM RecordReturns RR1
                              GROUP BY RR1.title) AS ProgramsWithNumberFamilies
                        LEFT JOIN RecordReturns RR2 ON RR2.title = ProgramsWithNumberFamilies.title
                        WHERE ProgramsWithNumberFamilies.Number_Return_Families >= 10) AS  ProgramsWithNumberFamiliesAndFamilies
                     LEFT JOIN Households H1 ON H1.hID = ProgramsWithNumberFamiliesAndFamilies.hID
                     WHERE H1.netWorth >= 8) AS ProgramsWithNetWorth
                GROUP BY ProgramsWithNetWorth.title, ProgramsWithNetWorth.Number_Return_Families) AS WealthyFamiliesbyProgram
           WHERE WealthyFamiliesbyProgram.Wealthy_Families > WealthyFamiliesbyProgram.Number_Return_Families / 2) AS QualitativePrograms
      LEFT JOIN ProgramRanks PR1 ON PR1.title = QualitativePrograms.title
      GROUP BY QualitativePrograms.title) AS QualitativeProgramsWithNumBadGrade
WHERE QualitativeProgramsWithNumBadGrade.Num_Bad_Grade = 0
        """)
        sql_res3 = dictfetchall(cursor)
    return render(request, 'queryResult.html', {'sql_res1': sql_res1,
                                                'sql_res2': sql_res2,
                                                'sql_res3': sql_res3})


def checkFamilyOrderExists(checked_hID):
    with connection.cursor() as cursor:
        cursor.execute("""SELECT DISTINCT hID
                          FROM Households""")
        all_hID = cursor.fetchall()
        for hID in all_hID:
            if hID[0] == int(checked_hID):
                return True
    return False


def checkTitleExists(checked_title):
    with connection.cursor() as cursor:
        cursor.execute("""SELECT DISTINCT title
                          FROM Programs""")
        all_title = cursor.fetchall()
        for title in all_title:
            if title[0] == str(checked_title):
                return True
    return False


def checkMoreThan3Programs(hID_order):
    with connection.cursor() as cursor:
        cursor.execute("""SELECT hID
                          FROM RecordOrders
                          GROUP BY hID
                          HAVING COUNT(title) = 3""")
        all_hID = cursor.fetchall()
        for hID in all_hID:
            if hID[0] == int(hID_order):
                return True
    return False


def alreadyOrderedProgramByOtherFamily(title_order, hID_order):
    with connection.cursor() as cursor:
        cursor.execute("""SELECT *
                          FROM RecordOrders""")
        all_records = cursor.fetchall()
        for record in all_records:
            if record[0] == str(title_order) and record[1] != int(hID_order):
                return True
    return False


def alreadyOrderedProgramBySameFamily(title, hID):
    with connection.cursor() as cursor:
        cursor.execute("""SELECT *
                          FROM RecordOrders""")
        all_records = cursor.fetchall()
        for record in all_records:
            if record[0] == str(title) and record[1] == int(hID):
                return True
    return False


def alreadyOrderedProgramBefore(title_order, hID_order):
    with connection.cursor() as cursor:
        cursor.execute("""SELECT *
                          FROM RecordReturns""")
        all_records = cursor.fetchall()
        for record in all_records:
            if record[0] == str(title_order) and record[1] == int(hID_order):
                return True
    return False


def forbiddenGenresForChildren(title_order, hID_order):
    with connection.cursor() as cursor:
        cursor.execute("""SELECT hID
                          FROM Households
                          WHERE ChildrenNum > 0""")
        families_with_children = cursor.fetchall()
        with_children = False
        for family in families_with_children:
            if family[0] == int(hID_order):
                with_children = True
        cursor.execute(""" SELECT title
                           FROM Programs
                           WHERE genre = 'Adults only' OR genre = 'Reality'""")
        forbidden_genres = cursor.fetchall()
        genre = False
        for program in forbidden_genres:
            if program[0] == str(title_order):
                genre = True
    return with_children and genre


def errorPossible(hID, title, case):
    error_case = []
    if case == 0:
        if not checkFamilyOrderExists(hID):
            error_case.append("hID does not exist")

        if not checkTitleExists(title):
            error_case.append("title does not exist")

        if checkMoreThan3Programs(hID):
            error_case.append("already have 3 programs")

        if alreadyOrderedProgramByOtherFamily(title, hID):
            error_case.append("already ordered program by other family")

        if alreadyOrderedProgramBySameFamily(title, hID):
            error_case.append("already ordered program by this family")

        if alreadyOrderedProgramBefore(title, hID):
            error_case.append("already ordered before")

        if forbiddenGenresForChildren(title, hID):
            error_case.append("not adequate program")

    else:
        if not checkFamilyOrderExists(hID):
            error_case.append("hID does not exist")

        if not checkTitleExists(title):
            error_case.append("title does not exist")

        if not alreadyOrderedProgramBySameFamily(title, hID):
            error_case.append("not belongs to this family")

    error_case.append("no error")
    return error_case


def alreadyRankedBefore(title_rank, hID_rank):
    with connection.cursor() as cursor:
        cursor.execute("""SELECT *
                          FROM ProgramRanks""")
        all_records = cursor.fetchall()
        for record in all_records:
            if record[0] == str(title_rank) and record[1] == int(hID_rank):
                return True
    return False


def recordsManagement(request):
    error_case = []
    if request.method == "POST" and request.POST:
        if 'new_hID_order' in request.POST and 'new_title_order' in request.POST:
            hID_order = request.POST["new_hID_order"]
            title_order = request.POST["new_title_order"]
            error_case = errorPossible(hID_order, title_order, 0)

            if error_case[0] == "no error":
                orderTable = Recordorders(hid=Households(hid=hID_order),
                                          title=Programs(title=title_order))
                orderTable.save()

        if 'new_hID_return' in request.POST and 'new_title_return' in request.POST:
            hID_return = request.POST["new_hID_return"]
            title_return = request.POST["new_title_return"]
            error_case = errorPossible(hID_return, title_return, 1)

            if error_case[0] == "no error":
                member = Recordorders.objects.get(hid=hID_return, title=title_return)
                member.delete()

                Recordreturns.objects.create(hid=Households(hid=hID_return),
                                             title=Programs(title=title_return))

    error_case.append("no error")
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT TOP 3 NumTotalByFamily.hID, NumTotalByFamily.Num_Ordered_Programs + NumTotalByFamily.Num_Returned_Programs AS Total_Num_Programs
    FROM(SELECT NumberReturnedByFamily.hID, NumberReturnedByFamily.Num_Returned_Programs,
                COALESCE(NumberOrdererByFamily.Num_Ordered_Programs, 0) AS Num_Ordered_Programs
         FROM(SELECT RR1.hID, COUNT(DISTINCT RR1.title) AS Num_Returned_Programs
              FROM RecordReturns RR1
              GROUP BY RR1.hID) AS NumberReturnedByFamily
         LEFT JOIN (SELECT RO1.hID, COUNT(DISTINCT RO1.title) AS Num_Ordered_Programs
                    FROM RecordOrders RO1
                    GROUP BY hID) AS NumberOrdererByFamily ON NumberOrdererByFamily.hID = NumberReturnedByFamily.hID) AS NumTotalByFamily
    ORDER BY Total_Num_Programs DESC, NumTotalByFamily.hID
            """)
        sql_res = dictfetchall(cursor)
    return render(request, 'recordsManagement.html', {'error_case': error_case[0],
                                                      'sql_res': sql_res})


def rankings(request):
    n = 6
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT DISTINCT hID
        FROM HouseHolds
        """)
        sql_hID = dictfetchall(cursor)

        cursor.execute("""
        SELECT DISTINCT title
        FROM Programs
        """)
        sql_title = dictfetchall(cursor)

        cursor.execute("""
        SELECT DISTINCT genre
        FROM Programs
        GROUP BY genre
        HAVING COUNT(DISTINCT title) >= 5
         """)
        sql_genre = dictfetchall(cursor)
        sql_min_rank = {}
        sql_min_rank1 = {}

    if request.method == "POST" and request.POST:
        if "new_hID_rank" in request.POST and "new_title_rank" in request.POST and "new_rank" in request.POST:
            hID_rank = request.POST["new_hID_rank"]
            title_rank = request.POST["new_title_rank"]
            new_rank = request.POST["new_rank"]

            if alreadyRankedBefore(title_rank, hID_rank):
                Programranks.objects.filter(title=title_rank, hid=hID_rank).delete()

            Programranks.objects.create(hid=Households(hid=hID_rank),
                                        title=Programs(title=title_rank),
                                        rank=new_rank)

        if "selected_genre" in request.POST and "min_rank" in request.POST:
            with connection.cursor() as cursor:
                genre = request.POST["selected_genre"]
                min_rank = request.POST["min_rank"]

                cursor.execute(""" SELECT TOP 5 ProgramsByGenre.title,CAST(AVG(CAST(PR2.rank AS DECIMAL(10,2))) AS DECIMAL(10,2)) AS averageRank
                                FROM (  SELECT DISTINCT PR1.title
                                        FROM ProgramRanks PR1
                                        LEFT JOIN Programs P ON P.title = PR1.title
                                        WHERE PR1.title NOT IN (SELECT DISTINCT title
                                                                FROM ProgramRanks
                                                                GROUP BY title
                                                                HAVING COUNT(IIF(rank< %s,1,NULL)) >0) AND P.genre = '%s')AS ProgramsByGenre
                                LEFT JOIN ProgramRanks PR2 ON PR2.title = ProgramsByGenre.title
                                GROUP BY ProgramsByGenre.title
                                ORDER BY averageRank DESC""" % (int(min_rank), str(genre)))
                sql_min_rank = dictfetchall(cursor)

                n = len(sql_min_rank)
                if n < 5:
                    cursor.execute("""SELECT TOP 5 *
                                    FROM (  SELECT TOP 5 ProgramsByGenre.title,CAST(AVG(CAST(PR2.rank AS DECIMAL(10,2))) AS DECIMAL(10,2)) AS averageRank
                                            FROM (  SELECT DISTINCT PR1.title
                                                    FROM ProgramRanks PR1
                                                    LEFT JOIN Programs P ON P.title = PR1.title
                                                    WHERE PR1.title NOT IN (SELECT DISTINCT title
                                                                            FROM ProgramRanks
                                                                            GROUP BY title
                                                                            HAVING COUNT(IIF(rank<%s,1,NULL)) >0) AND P.genre = '%s' ) AS ProgramsByGenre
                                            LEFT JOIN ProgramRanks PR2 ON PR2.title = ProgramsByGenre.title
                                            GROUP BY ProgramsByGenre.title
                                            ORDER BY averageRank DESC ) AS NotFiveLines
                                    UNION
                                    SELECT TOP %s title, 0
                                    FROM Programs
                                    WHERE genre = '%s' AND title NOT IN (SELECT TOP 5 ProgramsByGenre.title
        FROM (  SELECT DISTINCT PR1.title
                FROM ProgramRanks PR1
                LEFT JOIN Programs P ON P.title = PR1.title
                WHERE PR1.title NOT IN (SELECT DISTINCT title
                                        FROM ProgramRanks
                                        GROUP BY title
                                        HAVING COUNT(IIF(rank<%s,1,NULL)) >0) AND P.genre = '%s') AS ProgramsByGenre
        LEFT JOIN ProgramRanks PR2 ON PR2.title = ProgramsByGenre.title
        GROUP BY ProgramsByGenre.title)
                                    ORDER BY averageRank DESC ,title """ % (
                        int(min_rank), str(genre), 5 - n, str(genre), int(min_rank), str(genre)))
                    sql_min_rank1 = dictfetchall(cursor)
    return render(request, 'rankings.html', {'sql_hID': sql_hID,
                                             'sql_title': sql_title,
                                             'sql_genre': sql_genre,
                                             'sql_min_rank': sql_min_rank,
                                             'sql_min_rank1': sql_min_rank1,
                                             'n': n})
